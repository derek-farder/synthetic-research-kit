---
applyTo: 'clients/**,studies/**,personas/**,evidence/**,holdout/**,calibration/**'
---
Treat these paths as client-data paths except `clients/_template/`, `studies/_template/` and committed fictional examples.
Do not stage or commit their contents. Never use `git add -f` or `git add --force` for these paths.
Do not inspect `clients/*/holdout/**` (or legacy `holdout/**`) in normal Copilot work. Holdout data is reserved for the validation harness.
Never edit files under `clients/*/sources/raw/`; raw sources are immutable.
