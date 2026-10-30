# Synthetic Research Kit

A VS Code GitHub Copilot workspace for pressure-testing discussion guides with grounded synthetic personas. Synthetic output is always a hypothesis, never a research finding.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
git config core.hooksPath .githooks
./scripts/load-example.sh
python -m unittest discover -s tests -v
```

Open the repository in VS Code with GitHub Copilot Chat enabled. The workspace includes repository-wide instructions, two custom agents, and six workflow skills.

## Key commands

```bash
./scripts/persona-lab lint --persona personas/dana.md --evidence evidence/evidence.json --out calibration/dana/lint
./scripts/persona-lab all --persona personas/dana.md --others personas --evidence evidence/evidence.json --holdout holdout --probes calibration/probes/dana.json --out calibration/dana/mock --mock
python scripts/check_study.py studies/2026-10-infusion-pump
python scripts/export_synthesis.py studies/2026-10-infusion-pump
```

The included model backend is deterministic mock-only. It verifies plumbing but cannot calibrate a persona. Add an approved live model adapter before real calibration.
