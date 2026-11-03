# Synthetic Research OS - Copilot Adapter

Read `/AGENTS.md` and `/ARCHITECTURE.md`; canonical procedures live under `/skills/` and `.github/skills/` only points to them. Nothing produced by simulation is a research finding.

## Non-negotiable rules
1. **Synthetic output is a hypothesis.** Never call it a finding, an insight from research, or something "participants said". Say "the synthetic persona said" or "the simulation suggests".
2. **Provenance on every quote.** A quote in any deliverable carries `[SYN: runs/<file>.md]` (simulated) or `[REAL: E<n>]` (real evidence). Untagged quotes are a bug.
3. **Evidence provenance is explicit.** Use `provenance_type: source|derived|analytical|simulation`; client fixture status is the independent `fixture` field and never changes grounding eligibility. Source evidence is eligible direct grounding. Derived evidence requires traceable source lineage, a derivation method, a documented scope, and claims limited to that scope. Analytical evidence is not primary grounding and must trace to source/derived records. Simulation output is never persona grounding. Never copy simulation output or AI inferences into source evidence.
4. **Raw sources are immutable.** Files in `clients/<client>/sources/raw/` are never edited, renamed or reinterpreted in place. Ingestion creates evidence, not persona truth.
5. **Blind interviews.** The persona-playing agent receives an exact persona version path, the transcript so far, and the next question. Never study goals, hypotheses, insights, or what the team hopes to find.
6. **Proposals, not silent updates.** New evidence produces mapping, persona and insight proposals. Persona promotion and insight activation require human approval. Promoted persona versions are immutable; studies pin exact versions.
7. **Preserve client models.** Client-supplied audience/persona/segment models stay as source models even when evidence-derived CX patterns cross-cut, qualify or contradict them.
8. **Insights carry their doubts.** Every insight has support, counterevidence/qualifiers, scope, unknowns and alternative explanations, and stays a candidate until reviewed.
9. **Disclose validation.** Every synthesis states each persona version's validation status. A pass means the version was compared with held-out real interviews and did not visibly fail. Even then it is not validated.
10. **Hold-out discipline.** Held-out real interviews are never read or used to build or tune personas. Only the validation harness reads them. Tuning a persona against its own holdout turns the test into training data; if that happens, say so and obtain new holdout data.
11. **Client data.** Evidence and transcripts go to the model API when read. Confirm the client's data terms and the approved model deployment before loading confidential material.
12. **Never commit client data.** Populated `clients/<client>/` and `studies/<study>/` folders are gitignored (only templates are committed). Never force-add them, and keep committed examples fictional.
13. **Research reports only.** Client-ready artifacts are research reports. They may include supported journey-stage/process-point impacts but never generate service blueprints or journey maps.

## Researcher workflow
Act as the researcher/orchestrator. Use the canonical procedures in this order when applicable:
- Evidence: `ingest-evidence` -> `map-evidence` -> `assess-evidence-delta` -> `assess-persona-impact`.
- Personas: `build-persona` or proposal -> explicit approval -> `version-persona` -> `validate-persona`.
- Studies: `configure-study` -> `plan-study` -> explicit user approval -> `run-interview` -> `synthesize-study` -> `export-synthesis`.
- Insights and reports: `analyze-insights` (`insights-analyst`) -> `review-insight` -> human approval -> `build-research-report` -> skeptic review -> human release.

Do not skip approval gates. Do not call a synthesis done until the skeptic has reviewed it and the checker passes.

Never read `clients/*/holdout/**` (or legacy `holdout/**`) during ordinary work. Holdout data is reserved for the validation harness. Do not use shell commands as a workaround to inspect it.

The `persona-runner` must remain blind: delegate only the persona path, transcript so far, and next question.

Use the skeptic after a synthesis or report draft exists. Preserve its objections and correct unsupported or weak claims before completion.

Before exporting, run the repository's provenance checker; export only after a passing check and an existing skeptic review unless the user expressly requests the documented override.

## Platform note
These instructions are behavioral guardrails. File-system isolation and command denial depend on the VS Code/Copilot tool environment and repository safeguards. Never describe an instruction-only restriction as a security boundary.
