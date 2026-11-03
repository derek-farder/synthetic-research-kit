# START HERE
## Add new evidence
1. Put approved files in `clients/<client>/sources/raw/`. Never edit them afterwards; add a corrected file as a new source.
2. Run `python scripts/ingest_sources.py clients/<client>`.
3. Review source metadata. Ask the agent to map the new evidence and produce an evidence delta.
4. Review proposed construct, audience/persona and insight impacts.
5. Approve persona changes before a new immutable version becomes current (`python scripts/promote_persona_version.py clients/<client> <proposal.json>`).
6. Re-run validation for changed persona versions.

## New persona
Use `build-persona` to draft a grounded proposal (version 1.0), lint it with `scripts/persona-lab lint`, approve it, then promote it with `version-persona`. Reserve holdout interviews before reading any source material.

## New study
Run `python scripts/new_study.py <study-id>`, then edit `study.json` to select client, method, report output, and exact persona versions. Planning must stop for approval before simulation. `python scripts/check_study.py studies/<study-id>` enforces provenance tags, version pins, and validation disclosure.

## Evidence layers
Raw source = untouched input. Evidence = addressable observation/value. Mapping = interpretation. Claim = evidence-backed persona statement. Signal = pattern across evidence. Insight = reviewed interpretation. Opportunity/feature idea = hypothesis to test.

## Existing personas/segments
Treat client-supplied persona/segment models as inputs, not truth. Preserve the original model while evidence-derived CX patterns can cross-cut, qualify, split or contradict it.

## Legacy data
Older working data used flat `personas/`, `evidence/`, `holdout/` and `calibration/` folders. Migrate it with `python scripts/migrate_legacy_client.py clients/<client> [--from <legacy-root>] --dry-run`, then without `--dry-run`. See `docs/MIGRATION.md`.

## Platforms
Canonical procedures live under `/skills/`. GitHub Copilot adapter: `.github/`. Claude Code adapter: `.claude/`.

## Before client work
Confirm model/deployment approval, client data terms, holdout separation, Git exclusions (`git config core.hooksPath .githooks`), and successful fictional tests. Never commit populated client or study data.
