---
name: plan-study
description: Plan a synthetic study and stop at approval gate.
---
# plan-study
- Start from a configured study (`configure-study`): `study.json` names the client, method, output and exact persona versions.
- Read each pinned persona version's `validation_status` in `clients/<client>/personas/persona-registry.json` and disclose it in the plan.
- Write `question.md`, private `hypotheses.md`, and `protocol.md` with `status: draft`, following `methods/<method>/METHOD.md`.
- Use 6-10 core questions: behavior first, attitudes next, hypotheticals last. Keep wording neutral; include follow-ups and at least one contradiction/workaround probe.
- Where journey stages or process points matter, use them as probe and coding dimensions only; do not plan a journey map or service blueprint.
- Specify personas and versions, rationale, runs per persona (default 3), framing per run, transcript naming, coding plan and what real research would add.
- Stop after presenting the plan. Do not change protocol status to approved or run interviews until the user explicitly approves.
- Report persona versions/statuses, planned interview-turn count and the question with the greatest uncertainty.
