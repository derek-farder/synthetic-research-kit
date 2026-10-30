#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f evidence/evidence.json ]; then echo "Refusing: evidence/evidence.json already exists"; exit 1; fi
cp examples/personas/*.md personas/
cp examples/evidence/evidence.json evidence/
cp examples/holdout/*.json holdout/
cp examples/probes/*.json calibration/probes/
cp -R examples/study studies/2026-10-infusion-pump
printf 'Loaded fictional example. Files remain gitignored.
'
