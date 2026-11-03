# Architecture
This is a research system, not a service-blueprint or journey-map production suite. Journey stages and process points are analytical dimensions inside evidence, insights, studies, and reports.

## Portable engines
- Evidence Engine: raw sources -> registration -> normalized evidence -> mappings/constructs.
- Audience Engine: imported audience models, evidence-derived patterns, persona claims, immutable versions, change rationale.
- Insights Engine: signals, change, contradictions, whitespace, feature hypotheses, segment evolution, journey-stage/process-point impacts.
- Validation Engine: grounding, leakage, backtest, coherence, framing resistance, abstention, distinctiveness; future cross-model stability.
- Research Engine: methods, studies, blind simulation, coding, synthesis.
- Report Engine: research-report contracts and downstream client-ready artifacts; no blueprint generation.
- Platform adapters: GitHub Copilot and Claude Code expose the same canonical methodology.

Knowledge flow:
`raw -> ingestion batch -> evidence -> mapping -> claim/signal -> reviewed persona/insight version -> study -> synthesis -> research report`

Human gates: mapping changes that alter audience meaning; persona promotion; insight activation; study approval before simulation; client-ready report release.

## Client package
```
clients/<client>/
  CLIENT.md
  sources/raw/                 immutable raw files
  sources/source-registry.json
  evidence/                    evidence.jsonl (normalized), evidence.json (legacy curated excerpts),
                               mappings.jsonl, constructs.json, audience-models.json, ingestion-batches.json
  personas/                    persona-registry.json, proposals/, versions/<id>/<version>.md
  insights/insight-registry.json
  holdout/                     validation-only
  validation/                  probes/, <id>/<version>/<run>/
```
Studies live in `studies/<study>/` and pin `client` and exact persona versions in `study.json`. Populated client and study folders are gitignored.

Legacy flat data (`personas/`, `evidence/`, `holdout/`, `calibration/` at the repo root, under `clients/`, or inside a client folder) is migrated with `scripts/migrate_legacy_client.py`; see `docs/MIGRATION.md`. `check_study.py` still accepts the legacy flat layout so earlier studies and tests keep working.
