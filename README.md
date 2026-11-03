# Synthetic Research OS v3
Platform-agnostic, evidence-first research tooling for grounded synthetic personas, research simulation, insight discovery, persona evolution, validation, and client-ready research reporting.

**Synthetic output is hypothesis, not research evidence.** Start with `START-HERE.md`; architecture is in `ARCHITECTURE.md`.

## macOS setup
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
git config core.hooksPath .githooks
./scripts/load-example.sh
python -m unittest discover -s tests -v
```

Open the repository in VS Code with GitHub Copilot Chat, or in Claude Code. Both adapters expose the same canonical skills under `/skills/` and the `persona-runner`, `insights-analyst` and `skeptic` agents.

## Key commands
```bash
python scripts/new_client.py <client-id>
python scripts/ingest_sources.py clients/<client-id>
python scripts/promote_persona_version.py clients/<client-id> <proposal.json>
./scripts/persona-lab lint --persona clients/fictional-medtech/personas/versions/dana/1.0.md --evidence clients/fictional-medtech/evidence --out clients/fictional-medtech/validation/dana/1.0/lint
./scripts/persona-lab all --persona clients/fictional-medtech/personas/versions/dana/1.0.md --evidence clients/fictional-medtech/evidence --holdout clients/fictional-medtech/holdout --probes clients/fictional-medtech/validation/probes/dana.json --out clients/fictional-medtech/validation/dana/1.0/mock --mock
python scripts/new_study.py <study-id>
python scripts/check_study.py studies/2026-10-infusion-pump
python scripts/export_synthesis.py studies/2026-10-infusion-pump
python scripts/migrate_legacy_client.py clients/<client-id> --dry-run
```

The included model backend is deterministic mock-only. It verifies plumbing but cannot validate a persona. Add an approved live model adapter before real validation.
