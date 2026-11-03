---
name: build-persona
description: Draft a new evidence-grounded persona as a proposal for first promotion, preserving holdout separation.
---
# build-persona
- Establish which interviews are holdouts before reading source material; they live in `clients/<client>/holdout/`. Do not read holdouts.
- Confirm source material is approved for model processing and registered through `ingest-evidence`; fixture status is not a proxy for provenance.
- If the client supplied audience/persona/segment models, keep them as source models in `evidence/audience-models.json` and list the ones used in `derived_from_audience_models`. Evidence-derived CX patterns may cross-cut them; never overwrite the supplied model.
- Draft one claim per line: `- [E1, E2] behavior: ...`. Use `[]` for an explicit inference. Include at least three behavioral claims.
- Write the draft to `clients/<client>/personas/proposals/<id>-1.0.md` with a proposal JSON (`schemas/persona-proposal.schema.json`) carrying reasoning and evidence delta.
- Run `scripts/persona-lab lint --persona <draft> --evidence clients/<client>/evidence --out clients/<client>/validation/<id>/1.0-draft/lint`.
- Fix errors and report warnings, grounding coverage, thick-grounding coverage and thin/inferred claims.
- Stop for human approval. Promotion is `version-persona`; the new version starts `not-run` (uncalibrated) until `validate-persona` completes.

## Grounding eligibility

Persona claims may use:

- `provenance_type: source` as direct grounding evidence.
- `provenance_type: derived` only when `source_lineage`, a reproducible
  `derivation_method`, and `scope` are recorded, lineage resolves to
  eligible source/derived evidence, and the claim stays within that scope.

Do not use:

- `provenance_type: analytical` as primary evidence. Analytical
  records must include `source_lineage` to source/derived evidence.
- `provenance_type: simulation` to ground a persona.

`fixture` indicates whether the research environment is fabricated for
testing. It does not determine grounding eligibility: source evidence can
be eligible when `fixture: true`, while simulation evidence is ineligible
regardless of fixture status.

Legacy evidence with `synthetic: false` is read as source provenance and
`synthetic: true` as simulation provenance during migration. The current
evidence schema requires `provenance_type` and `fixture`.