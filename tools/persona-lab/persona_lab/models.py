"""Provider-neutral chat-model adapters for persona validation."""

from __future__ import annotations

import json
import os
import datetime
from pathlib import Path
from threading import Lock
from dataclasses import dataclass, field
from typing import Callable, Mapping, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


class ModelConfigurationError(ValueError):
    """Raised when a validation model is not configured safely."""


class ModelRequestError(RuntimeError):
    """Raised when a configured model cannot complete a request."""


class ChatModel(Protocol):
    def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        """Return the model's assistant response."""


@dataclass(frozen=True)
class ModelResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None


def complete_with_usage(
    model: ChatModel,
    messages: Sequence[Mapping[str, str]],
    *,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> ModelResponse:
    """Call a model with telemetry when supported, preserving older adapters."""
    method = getattr(model, "complete_with_usage", None)
    if method is None:
        return ModelResponse(
            model.complete(messages, temperature=temperature, max_tokens=max_tokens)
        )
    return method(messages, temperature=temperature, max_tokens=max_tokens)


@dataclass(frozen=True)
class ModelConfig:
    role: str
    provider: str
    model: str
    endpoint: str
    api_version: str
    auth_method: str
    credential_env: str
    credential: str = field(repr=False)


def load_model_config(
    role: str,
    model_override: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> ModelConfig:
    """Load one independently configured persona or judge model."""
    normalized_role = role.strip().upper()
    if normalized_role not in {"PERSONA", "JUDGE"}:
        raise ModelConfigurationError("model role must be PERSONA or JUDGE")

    env = os.environ if environ is None else environ
    prefix = f"PERSONA_LAB_{normalized_role}_"
    provider = env.get(prefix + "PROVIDER", "").strip().lower()
    model = (model_override or env.get(prefix + "MODEL", "")).strip()
    endpoint = env.get(prefix + "ENDPOINT", "").strip().rstrip("/")
    api_version = env.get(prefix + "API_VERSION", "").strip()
    auth_method = env.get(prefix + "AUTH_METHOD", "").strip().lower()

    missing = [
        name
        for name, value in (
            ("PROVIDER", provider),
            ("MODEL", model),
            ("ENDPOINT", endpoint),
            ("API_VERSION", api_version),
            ("AUTH_METHOD", auth_method),
        )
        if not value
    ]
    if missing:
        names = ", ".join(prefix + name for name in missing)
        raise ModelConfigurationError(f"missing model configuration: {names}")

    parsed_endpoint = urlsplit(endpoint)
    if (
        parsed_endpoint.scheme != "https"
        or not parsed_endpoint.hostname
        or parsed_endpoint.username
        or parsed_endpoint.password
        or parsed_endpoint.query
        or parsed_endpoint.fragment
    ):
        raise ModelConfigurationError(
            f"{prefix}ENDPOINT must be an HTTPS URL without embedded credentials or query"
        )

    if auth_method == "api-key":
        credential_env = prefix + "API_KEY"
    elif auth_method == "bearer-token":
        credential_env = prefix + "BEARER_TOKEN"
    else:
        raise ModelConfigurationError(
            f"{prefix}AUTH_METHOD must be api-key or bearer-token"
        )

    credential = env.get(credential_env, "").strip()
    if not credential:
        raise ModelConfigurationError(
            f"missing credential in {credential_env}; provide it through the approved secret store"
        )

    return ModelConfig(
        role=normalized_role.lower(),
        provider=provider,
        model=model,
        endpoint=endpoint,
        api_version=api_version,
        auth_method=auth_method,
        credential_env=credential_env,
        credential=credential,
    )


class AzureOpenAIChatModel:
    """Azure OpenAI chat-completions adapter using only the Python standard library."""

    def __init__(
        self,
        config: ModelConfig,
        opener: Callable[..., object] = urlopen,
        timeout: float = 60.0,
    ) -> None:
        if config.provider != "azure-openai":
            raise ModelConfigurationError(
                "AzureOpenAIChatModel requires provider azure-openai"
            )
        self.config = config
        self._opener = opener
        self._timeout = timeout

    def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        return self.complete_with_usage(
            messages, temperature=temperature, max_tokens=max_tokens
        ).content

    def complete_with_usage(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> ModelResponse:
        url = (
            f"{self.config.endpoint}/openai/deployments/"
            f"{quote(self.config.model, safe='')}/chat/completions?"
            f"{urlencode({'api-version': self.config.api_version})}"
        )
        headers = {"Content-Type": "application/json"}
        if self.config.auth_method == "api-key":
            headers["api-key"] = self.config.credential
        else:
            headers["Authorization"] = "Bearer " + self.config.credential

        payload = json.dumps(
            {
                "messages": list(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        ).encode("utf-8")
        request = Request(url, data=payload, headers=headers, method="POST")

        try:
            response = self._opener(request, timeout=self._timeout)
            with response:
                body = response.read()
        except HTTPError as exc:
            raise ModelRequestError(
                f"Azure OpenAI request failed with HTTP {exc.code}"
            ) from None
        except URLError as exc:
            raise ModelRequestError(
                f"Azure OpenAI request could not reach the configured endpoint: {exc.reason}"
            ) from None

        try:
            data = json.loads(body)
            content = data["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise ModelRequestError(
                "Azure OpenAI returned an invalid chat-completions response"
            ) from exc
        if not isinstance(content, str):
            raise ModelRequestError(
                "Azure OpenAI response content must be a string"
            )
        usage = data.get("usage")
        if usage is not None and not isinstance(usage, dict):
            raise ModelRequestError(
                "Azure OpenAI returned invalid token-usage metadata"
            )
        usage = usage or {}
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        return ModelResponse(
            content=content,
            input_tokens=(
                input_tokens
                if type(input_tokens) is int and input_tokens >= 0
                else None
            ),
            output_tokens=(
                output_tokens
                if type(output_tokens) is int and output_tokens >= 0
                else None
            ),
        )


_TELEMETRY_LOCK = Lock()


def append_model_call_telemetry(
    path: str | Path,
    *,
    operation_type: str,
    config: ModelConfig,
    input_tokens: int | None,
    output_tokens: int | None,
    persona_id: str | None = None,
    persona_version: str | None = None,
    study_id: str | None = None,
    client_id: str | None = None,
) -> dict[str, object]:
    """Append metadata-only telemetry; prompts, responses, and credentials are excluded."""
    event: dict[str, object] = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "operation_type": operation_type,
        "provider": config.provider,
        "model": config.model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "persona_id": persona_id,
        "persona_version": persona_version,
        "study_id": study_id,
        "client_id": client_id,
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with _TELEMETRY_LOCK:
        with target.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
    return event


AdapterFactory = Callable[[ModelConfig], ChatModel]
_ADAPTERS: dict[str, AdapterFactory] = {
    "azure-openai": AzureOpenAIChatModel,
}


def register_adapter(provider: str, factory: AdapterFactory) -> None:
    """Register a provider implementation without changing validation callers."""
    name = provider.strip().lower()
    if not name:
        raise ModelConfigurationError("provider name cannot be empty")
    _ADAPTERS[name] = factory


def create_chat_model(
    config: ModelConfig,
    opener: Callable[..., object] = urlopen,
) -> ChatModel:
    """Create the configured provider through the shared chat-model interface."""
    factory = _ADAPTERS.get(config.provider)
    if factory is None:
        supported = ", ".join(sorted(_ADAPTERS))
        raise ModelConfigurationError(
            f"unsupported provider {config.provider!r}; registered providers: {supported}"
        )
    if factory is AzureOpenAIChatModel:
        return AzureOpenAIChatModel(config, opener=opener)
    return factory(config)
