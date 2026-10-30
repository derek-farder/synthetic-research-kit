---
name: build-persona
description: Build a grounded synthetic persona from approved real research evidence while preserving holdout separation.
---
# Build persona
- Establish which interviews are holdouts before reading source material. Do not read holdouts.
- Confirm source material is real research material and approved for model processing.
- Store verbatim source excerpts in `evidence/evidence.json` with source ids and `synthetic: false`.
- Draft one persona claim per line. Cite evidence ids; use `[]` for an explicit inference.
- Include at least three behavioral claims.
- Run `scripts/persona-lab lint --persona personas/<id>.md --evidence evidence/evidence.json --out calibration/<id>/lint`.
- Fix errors and report warnings, grounding coverage, thick-grounding coverage and thin/inferred claims.
- Treat the persona as uncalibrated until calibration completes.
