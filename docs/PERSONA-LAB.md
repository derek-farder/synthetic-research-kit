# Persona Lab model configuration

Persona Lab exposes a provider-neutral chat interface. Azure OpenAI is the
first built-in provider; no provider or deployment is selected by default.
Persona and judge models are configured independently. Use a distinct judge
model when the approved deployment permits it.

The adapter reads configuration from environment variables, not from client
packages or repository files:

| Variable suffix | Required | Meaning |
|---|---:|---|
| `PROVIDER` | yes | Provider identifier; currently `azure-openai` |
| `MODEL` | unless supplied as an override | Azure deployment name for that role |
| `ENDPOINT` | yes | HTTPS Azure resource endpoint, without embedded credentials or query |
| `API_VERSION` | yes | Approved Azure OpenAI API version |
| `AUTH_METHOD` | yes | `api-key` or `bearer-token` |
| `API_KEY` | for `api-key` | Secret from the approved secret store |
| `BEARER_TOKEN` | for `bearer-token` | Short-lived token supplied by an approved identity mechanism |

Prefix each variable with `PERSONA_LAB_PERSONA_` or
`PERSONA_LAB_JUDGE_`. For example, configure
`PERSONA_LAB_PERSONA_PROVIDER` and `PERSONA_LAB_JUDGE_PROVIDER` separately.
Do not store secrets in the repository, client data, command-line arguments,
or validation reports. The adapter does not acquire or refresh identity tokens;
an approved external mechanism must provide the bearer token.

The Python interface is `ChatModel.complete(messages, temperature, max_tokens)`.
Providers are registered through `register_adapter`; callers use
`create_chat_model` without depending on provider-specific request details.
`load_model_config("persona", ...)` and `load_model_config("judge", ...)`
resolve independent role configurations. An explicit model override takes
precedence over that role's `MODEL` variable.

Mock validation remains usable without live credentials. Mock output is only
for plumbing checks and cannot establish persona validation status. Do not
invoke validation against holdout until the client has approved the model
deployment and data-processing terms.

The `persona-lab leakage` command runs the deterministic source/holdout overlap
check through the harness without invoking any model. It records only the
leakage dimension as PASS or INVALID; behavioral backtest, coherence,
abstention, framing resistance and distinctiveness remain NOT-RUN. This
leakage-only result does not update a persona's overall `validation_status`.
