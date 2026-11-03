---
name: build-persona
description: Draft a new evidence-grounded persona as a proposal for first promotion, preserving holdout separation.
---
# build-persona
- Establish which interviews are holdouts before reading source material; they live in `clients/<client>/holdout/`. Do not read holdouts.
- Confirm source material is real research material, approved for model processing, and registered through `ingest-evidence`.
- Ground claims only in evidence ids from `clients/<client>/evidence/` (`evidence.json` curated excerpts and/or `evidence.jsonl` normalized records) with `synthetic: false`.
- If the client supplied audience/persona/segment models, keep them as source models in `evidence/audience-models.json` and list the ones used in `derived_from_audience_models`. Evidence-derived CX patterns may cross-cut them; never overwrite the supplied model.
- Draft one claim per line: `- [E1, E2] behavior: ...`. Use `[]` for an explicit inference. Include at least three behavioral claims.
- Write the draft to `clients/<client>/personas/proposals/<id>-1.0.md` with a proposal JSON (`schemas/persona-proposal.schema.json`) carrying reasoning and evidence delta.
- Run `scripts/persona-lab lint --persona <draft> --evidence clients/<client>/evidence --out clients/<client>/validation/<id>/1.0-draft/lint`.
- Fix errors and report warnings, grounding coverage, thick-grounding coverage and thin/inferred claims.
- Stop for human approval. Promotion is `version-persona`; the new version starts `not-run` (uncalibrated) until `validate-persona` completes.
