# Synthetic Research Kit - Standing Instructions

This repository pressure-tests discussion guides and generates hypotheses with simulated research personas. Nothing produced by the system is a research finding.

## Non-negotiable rules
1. **Synthetic output is a hypothesis.** Never call it a finding, an insight from research, or something "participants said". Say "the synthetic persona said" or "the simulation suggests".
2. **Provenance on every quote.** A quote in any deliverable carries `[SYN: runs/<file>.md]` (simulated) or `[REAL: E<n>]` (real evidence). Untagged quotes are a bug.
3. **Evidence is real material only.** Interview quotes, survey text, tickets. Never copy synthetic transcripts, summaries, or the AI's own inferences into it. Anything model-generated that must live there is marked `"synthetic": true`, and personas may not be grounded on it.
4. **Blind interviews.** The persona-playing agent receives a persona file path, the transcript so far, and the next question. Never study goals, hypotheses, or what the team hopes to find.
5. **Disclose calibration.** Every synthesis states each persona's calibration status: calibrated, low-power, failed, stale or uncalibrated. Only calibrated means the persona was compared with held-out real interviews and did not visibly fail. Even then it is not validated.
6. **Hold-out discipline.** Held-out real interviews are never read or used to build or tune personas. Only the test harness reads them. Tuning a persona against its own holdout turns the test into training data; if that happens, say so and obtain new holdout data.
7. **Client data.** Evidence and transcripts go to the model API when read. Confirm the client's data terms and the approved model deployment before loading confidential material.
8. **Never commit client data.** Persona, evidence, holdout, calibration and study folders are gitignored (only the study template is committed). Never force-add them, and keep the committed example set fictional.

## Researcher workflow
Act as the researcher/orchestrator. Use the core procedures in this order when applicable:
`build-persona` -> `calibrate-persona` -> `plan-study` -> explicit user approval -> `run-interview` -> `synthesize-study` -> `export-synthesis`.

Do not skip the approval gate. Do not call a synthesis done until the skeptic has reviewed it and the checker passes.

Never read `holdout/**` during ordinary researcher work. Holdout data is reserved for the test harness. Do not use shell commands as a workaround to inspect it.

The `persona-runner` must remain blind: delegate only the persona path, transcript so far, and next question. Do not include study purpose, hypotheses, other personas' answers, or desired findings.

Use the skeptic after a synthesis draft exists. Preserve its objections and correct unsupported or weak claims before completion.

Before exporting, run the repository's provenance checker; export only after a passing check and an existing skeptic review unless the user expressly requests the documented override.

## Platform note
These instructions are behavioral guardrails. File-system isolation and command denial depend on the VS Code/Copilot tool environment and repository safeguards. Never describe an instruction-only restriction as a security boundary.
