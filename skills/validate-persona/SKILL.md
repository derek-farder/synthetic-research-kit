---
name: validate-persona
description: Run version-specific validation.
---
# validate-persona
Validation is pinned to one exact persona version and execution configuration (persona model, judge model, harness version). It is the only workflow that consumes holdout, and only through the harness; agents never open holdout files directly.

- Require a real model API configuration. `--mock` tests plumbing only and cannot establish any validation status.
- Configure persona and judge deployments independently through the provider-neutral adapter; see `docs/PERSONA-LAB.md`. Do not select a provider or deployment by default, and never store credentials in the repository.
- Require persona-specific holdout data in `clients/<client>/holdout/` and probes at `clients/<client>/validation/probes/<id>.json`. If probes are missing, draft consistency, framing, out-of-scope and distinctiveness probes for user review first.
- Prefer a judge model different from the persona model when available.
- Run `scripts/persona-lab all --persona clients/<client>/personas/versions/<id>/<version>.md --evidence clients/<client>/evidence --holdout clients/<client>/holdout --probes clients/<client>/validation/probes/<id>.json --out clients/<client>/validation/<id>/<version>/<YYYY-MM-DD>-<label>`.
- Exit 1 = FAIL; exit 2 = holdout leakage/INVALID (or harness configuration error).
- Derive status: INVALID => `invalid`; FAIL => `fail`; PASS/WARN with fewer than 10 held-out answers => `low-power`; PASS/WARN with 10+ => `pass`/`warn`.
- Write `STATUS.md` in the run folder with persona sha256, persona model and judge model, and update `validation_status` for that exact version in `persona-registry.json`. A model change or new persona version makes prior results `stale`.
- Report grounding, leakage, backtest, coherence, framing resistance, abstention and distinctiveness separately as PASS/WARN/FAIL/LOW-POWER/NOT-RUN/INVALID. Never produce one validity percentage. A pass means "not visibly broken against the holdout available", never validated.
