# Architecture
This is a research system, not a service-blueprint or journey-map production suite. Journey stages and process points are analytical dimensions inside evidence, insights, studies, and reports.

## Portable engines
- Evidence Engine: raw sources -> registration -> normalized evidence -> mappings/constructs. Evidence `provenance_type` (source, derived, analytical, simulation) is independent from client fixture status; fixture metadata never changes grounding eligibility.
- Audience Engine: imported audience models, evidence-derived patterns, persona claims, immutable versions, change rationale.
- Insights Engine: signals, change, contradictions, whitespace, feature hypotheses, segment evolution, journey-stage/process-point impacts.
- Validation Engine: grounding, leakage, backtest, coherence, framing resistance, abstention, distinctiveness; future cross-model stability.
- Research Engine: methods, studies, blind simulation, coding, synthesis.
- Report Engine: research-report contracts and downstream client-ready artifacts; no blueprint generation.
- Platform adapters: GitHub Copilot and Claude Code expose the same canonical methodology.
- Application boundary: shared clients, evidence, personas, insights, validation, studies, and reports services depend on repository interfaces. Filesystem repositories remain the persistence implementation; CLI/platform/UI adapters should call the same application services.
- Telemetry: model calls record operation, provider/model, token counts when reported, and relevant persona/study/client identifiers. Prompts, responses, and credentials are excluded from telemetry.

Knowledge flow:
`raw -> ingestion batch -> evidence -> mapping -> claim/signal -> reviewed persona/insight version -> study -> synthesis -> research report`

Human gates: mapping changes that alter audience meaning; persona promotion; insight activation; study approval before simulation; client-ready report release.

## Client package
```
clients/<client>/
  CLIENT.md
  client.json                  client id, fixture status, and real-data status
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

Before execution, `scripts/snapshot_study.py` freezes an approved v3.1 study's persona hashes and validation profiles, method/output contract versions, execution provider/model, run count, and limitations, and transitions it to `running`. The snapshot is historical and does not follow later validation-profile changes. Legacy v3 study files without this field remain valid.

Legacy flat data (`personas/`, `evidence/`, `holdout/`, `calibration/` at the repo root, under `clients/`, or inside a client folder) is migrated with `scripts/migrate_legacy_client.py`; see `docs/MIGRATION.md`. `check_study.py` still accepts the legacy flat layout so earlier studies and tests keep working.
