---
name: calibrate-persona
description: Calibrate a persona against held-out interviews using the persona-lab harness.
---
# Calibrate persona
- Require a real model API configuration for calibration. Mock mode tests plumbing only and cannot establish calibration.
- Require persona-specific holdout data and `calibration/probes/<id>.json`.
- If probes are missing, draft consistency, framing, out-of-scope and distinctiveness probes for user review before calibration.
- Prefer a judge model different from the persona model when available.
- Run the repository harness with persona, peers, evidence, holdout, probes and an output folder dated for the run.
- Interpret exit 1 as FAIL and exit 2 as holdout leakage/INVALID.
- Derive status from results: INVALID => uncalibrated; FAIL => failed; PASS/WARN with fewer than 10 held-out answers => low-power; PASS/WARN with 10+ => calibrated.
- Write `STATUS.md`, including persona hash and, for this VS Code port, record persona model and judge model. Treat a model change as stale.
- Describe calibrated as "not visibly broken against the holdout available", never validated.
