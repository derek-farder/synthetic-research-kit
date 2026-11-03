# Synthetic Research OS
Canonical procedures live under `skills/`; schemas under `schemas/`. Repository-wide operating rules: `.github/copilot-instructions.md` (Copilot) and `.claude/CLAUDE.md` (Claude Code), which share the same rules.

Specialists:
- Researcher/orchestrator: the main session; coordinates evidence, personas, studies and approvals.
- Persona Runner (`persona-runner`): blind, stateless simulated participant for one interview turn.
- Insights Analyst (`insights-analyst`): evidence-first exploration of signals, changes, contradictions, whitespace, feature hypotheses, segment evolution, and journey-stage/process-point impacts; seeks counterevidence and writes proposals only.
- Skeptic (`skeptic`): adversarial reviewer of syntheses and research reports.

Deterministic tools:
- `scripts/ingest_sources.py`: raw source registration and normalization.
- `scripts/promote_persona_version.py`: approved proposal -> immutable persona version.
- `scripts/persona-lab`: lint/backtest/coherence validation harness (the only holdout consumer).
- `scripts/check_study.py`: provenance, version-pin and validation-disclosure gate.
- `scripts/export_synthesis.py`: gated Word export of a checked synthesis.
- `scripts/migrate_legacy_client.py`: legacy flat client data -> v3 client package.

Safety boundaries:
- Holdout is validation-only; never inspect `clients/*/holdout/**` except through the harness.
- Raw source is not edited. Never use synthetic material as real evidence.
- Persona versions are immutable after promotion; studies pin exact versions.
- Research reports may discuss supported journey/process impacts but do not invent journey stages or backstage operations, and the system does not generate service blueprints or journey maps.
- Never force-add client-data paths to git. Keep committed examples fictional.
