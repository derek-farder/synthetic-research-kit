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

Mock validation remains usable without live credentials for plumbing only.
It reports `MOCK`, removes mock verdicts, and never writes persona validation
status. A live dimension requires a configured persona model for actual
response generation and an independently configured judge model for rubric
evaluation. Each behavioral dimension is run independently; no overall
validity percentage is produced.

The `persona-lab leakage` command runs the deterministic source/holdout overlap
check through the harness without invoking any model. It records only the
leakage dimension as PASS or INVALID; behavioral backtest, coherence,
abstention, framing resistance and distinctiveness remain NOT-RUN. This
leakage-only result does not update a persona's overall `validation_status`.

Behavioral dimensions accept versioned JSON probe sets. Probe formats use a
top-level `version` and `probes` list; abstention cases declare `scope` as
`answerable` or `out_of_scope`. Framing resistance uses a `scenarios` list,
each with at least two equivalent `framings`. Distinctiveness also requires
`--others` with comparison persona paths. `--model` overrides the persona
deployment; `--judge-model` independently overrides the judge deployment.
Live results include persona hash, dimension, provider/deployment metadata,
persona and judge prompt versions, rubric/probe/harness versions, generation
parameters, per-call token usage when reported, and judge rationale.
Distinctiveness results also record each comparison persona ID, version, and
hash. Mock runs do not write these results into persona validation profiles.

Backtest requires an explicit `backtest-comparison-v1` design mapping each
holdout ID and exact holdout question to a generated probe and a comparison
criterion. Only the controlled backtest path opens holdout data. The persona
generator receives the persona and declared probe only; the judge receives
the generated answer and selected holdout answer for evaluation. Record
holdout contamination with `persona-lab contaminate-holdout`; future runs
using the same revised-approach hash reject contaminated records.

Model-call telemetry is JSONL metadata only (operation, provider/model,
token counts, and relevant IDs); it does not persist prompts, model output,
or credentials. Set `PERSONA_LAB_TELEMETRY_PATH` or pass `--telemetry-path`
to select its location.
