---
applyTo: 'personas/**,evidence/**,holdout/**,calibration/**,studies/**'
---
Treat these paths as client-data paths except committed fictional examples and `studies/_template/`.
Do not stage or commit their contents. Never use `git add -f` or `git add --force` for these paths.
Do not inspect `holdout/**` in normal Copilot work. Holdout data is reserved for the calibration harness.
