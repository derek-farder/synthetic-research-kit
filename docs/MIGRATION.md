# Migrating legacy flat data
Before v3, working data lived in flat `personas/`, `evidence/`, `holdout/` and `calibration/` folders. v3 keeps everything for one client in `clients/<client>/` and versions personas.

| Legacy | v3 client package |
|---|---|
| `personas/<id>.md` | `personas/versions/<id>/1.0.md` + `personas/persona-registry.json` entry (sha256, `validation_status`) |
| `evidence/evidence.json` | `evidence/evidence.json` (unchanged; personas keep citing `E<n>` ids) |
| `calibration/probes/<id>.json` | `validation/probes/<id>.json` |
| `calibration/<id>/**` | `validation/<id>/legacy-unversioned/**` |
| `holdout/*` | `holdout/*` (moved without opening; left untouched for an in-place migration) |

```bash
python scripts/migrate_legacy_client.py clients/<client> --dry-run           # legacy folders inside the client folder
python scripts/migrate_legacy_client.py clients/<client> --from clients --dry-run   # flat clients/evidence, clients/personas, ...
```
Files move byte-for-byte and are verified by sha256; `MIGRATION.json` in the client folder records each move. Legacy `STATUS.md` values map to v3 statuses (`calibrated`->`pass`, `failed`->`fail`, `uncalibrated`->`not-run`), and become `stale` if the recorded persona hash no longer matches.

Studies completed before v3 have no `study.json`. Check them against their client package with `python scripts/check_study.py studies/<study> --client clients/<client>`; the checker resolves personas to the current version and warns that the study did not pin versions. Do not add a pin retroactively unless you know which version was used.
