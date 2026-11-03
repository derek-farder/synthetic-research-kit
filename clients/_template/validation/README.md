# Validation
Validation is pinned to exact persona version and execution configuration. Store reports/status here; keep holdout source material isolated.

- `probes/<persona-id>.json` - coherence probes (consistency, framing, out-of-scope, distinctiveness).
- `<persona-id>/<version>/<YYYY-MM-DD>-<label>/` - harness output (`results.json`, `report.md`) and `STATUS.md`.
- `<persona-id>/legacy-unversioned/` - results migrated from the legacy `calibration/` folder; not attributable to a version.
