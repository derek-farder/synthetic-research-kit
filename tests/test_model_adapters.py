import json
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/persona-lab"))
from persona_lab.models import (
    AzureOpenAIChatModel,
    ModelConfigurationError,
    ModelRequestError,
    create_chat_model,
    load_model_config,
)


def azure_environment(role, **values):
    prefix = f"PERSONA_LAB_{role.upper()}_"
    defaults = {
        "PROVIDER": "azure-openai",
        "MODEL": f"{role}-deployment",
        "ENDPOINT": "https://example.openai.azure.com",
        "API_VERSION": "2024-10-21",
        "AUTH_METHOD": "api-key",
        "API_KEY": f"{role}-secret",
    }
    return {prefix + key: value for key, value in (defaults | values).items()}


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.body


class ModelAdapterTests(unittest.TestCase):
    def test_persona_and_judge_configuration_are_independent(self):
        env = azure_environment("persona") | azure_environment(
            "judge", MODEL="separate-judge-deployment", AUTH_METHOD="bearer-token"
        )
        env["PERSONA_LAB_JUDGE_BEARER_TOKEN"] = "judge-token"
        del env["PERSONA_LAB_JUDGE_API_KEY"]

        persona = load_model_config("persona", environ=env)
        judge = load_model_config("judge", environ=env)

        self.assertEqual(persona.model, "persona-deployment")
        self.assertEqual(judge.model, "separate-judge-deployment")
        self.assertEqual(persona.auth_method, "api-key")
        self.assertEqual(judge.auth_method, "bearer-token")
        self.assertNotIn("persona-secret", repr(persona))
        self.assertNotIn("judge-token", repr(judge))

    def test_model_override_does_not_change_other_role(self):
        env = azure_environment("persona") | azure_environment("judge")
        persona = load_model_config("persona", "approved-persona-deployment", env)
        judge = load_model_config("judge", environ=env)

        self.assertEqual(persona.model, "approved-persona-deployment")
        self.assertEqual(judge.model, "judge-deployment")

    def test_provider_and_endpoint_are_required_without_defaults(self):
        with self.assertRaisesRegex(ModelConfigurationError, "PROVIDER"):
            load_model_config("persona", environ={})
        with self.assertRaisesRegex(ModelConfigurationError, "HTTPS URL"):
            load_model_config(
                "persona",
                environ=azure_environment("persona", ENDPOINT="http://localhost"),
            )

    def test_missing_secret_reports_variable_name_not_value(self):
        env = azure_environment("persona")
        del env["PERSONA_LAB_PERSONA_API_KEY"]

        with self.assertRaises(ModelConfigurationError) as caught:
            load_model_config("persona", environ=env)

        self.assertIn("PERSONA_LAB_PERSONA_API_KEY", str(caught.exception))
        self.assertNotIn("persona-secret", str(caught.exception))

    def test_azure_adapter_uses_api_key_and_returns_chat_content(self):
        config = load_model_config("persona", environ=azure_environment("persona"))
        captured = []

        def opener(request, timeout):
            captured.append((request, timeout))
            return FakeResponse(
                json.dumps({
                    "choices": [{"message": {"content": "READY"}}],
                    "usage": {"prompt_tokens": 12, "completion_tokens": 4},
                }).encode()
            )

        model = create_chat_model(config, opener=opener)
        response = model.complete(
            [{"role": "user", "content": "Reply READY."}], max_tokens=8
        )

        self.assertEqual(response, "READY")
        usage = model.complete_with_usage(
            [{"role": "user", "content": "Reply READY."}], max_tokens=8
        )
        self.assertEqual(usage.content, "READY")
        self.assertEqual(usage.input_tokens, 12)
        self.assertEqual(usage.output_tokens, 4)
        request, timeout = captured[0]
        self.assertIsInstance(request, Request)
        self.assertIn("/deployments/persona-deployment/", request.full_url)
        self.assertIn("api-version=2024-10-21", request.full_url)
        self.assertEqual(request.get_header("Api-key"), "persona-secret")
        self.assertEqual(timeout, 60.0)
        body = json.loads(request.data)
        self.assertEqual(body["messages"][0]["content"], "Reply READY.")
        self.assertEqual(body["max_tokens"], 8)

    def test_azure_adapter_supports_bearer_token_auth(self):
        env = azure_environment("judge", AUTH_METHOD="bearer-token")
        env["PERSONA_LAB_JUDGE_BEARER_TOKEN"] = "short-lived-token"
        del env["PERSONA_LAB_JUDGE_API_KEY"]
        config = load_model_config("judge", environ=env)
        captured = []

        def opener(request, timeout):
            captured.append(request.get_header("Authorization"))
            return FakeResponse(
                json.dumps({"choices": [{"message": {"content": "OK"}}]}).encode()
            )

        AzureOpenAIChatModel(config, opener=opener).complete(
            [{"role": "user", "content": "test"}]
        )
        self.assertEqual(captured, ["Bearer short-lived-token"])

    def test_http_errors_do_not_include_response_body_or_credentials(self):
        config = load_model_config("persona", environ=azure_environment("persona"))

        def opener(_request, timeout):
            raise HTTPError(
                "https://example.invalid",
                401,
                "unauthorized",
                None,
                None,
            )

        with self.assertRaises(ModelRequestError) as caught:
            AzureOpenAIChatModel(config, opener=opener).complete(
                [{"role": "user", "content": "test"}]
            )

        self.assertEqual(str(caught.exception), "Azure OpenAI request failed with HTTP 401")
        self.assertNotIn("persona-secret", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
