#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
C=clients/fictional-medtech
if [ -e "$C" ]; then echo "Refusing: $C already exists"; exit 1; fi
if [ -e studies/2026-10-infusion-pump ]; then echo "Refusing: studies/2026-10-infusion-pump already exists"; exit 1; fi
python3 scripts/new_client.py fictional-medtech >/dev/null
# Stage the committed fictional fixtures in the legacy flat shape, then migrate them into the v3 package.
mkdir -p "$C/personas" "$C/calibration/probes"
cp examples/personas/*.md "$C/personas/"
cp examples/evidence/evidence.json "$C/evidence/"
cp examples/holdout/*.json "$C/holdout/"
cp examples/probes/*.json "$C/calibration/probes/"
python3 scripts/migrate_legacy_client.py "$C" >/dev/null
cp -R examples/study studies/2026-10-infusion-pump
printf '{"client":"fictional-medtech","method":"interview","output":"research-report","personas":[{"id":"dana","version":"1.0"}],"runs_per_persona":1,"status":"complete"}\n' > studies/2026-10-infusion-pump/study.json
printf 'Loaded fictional example into %s and studies/2026-10-infusion-pump. Files remain gitignored.\n' "$C"
