# Synthetic Research Kit

Use `.github/copilot-instructions.md` as the repository-wide operating rules for this project.

## Architecture
- Main Copilot session: researcher/orchestrator.
- `.github/agents/persona-runner.agent.md`: blind, stateless simulated participant.
- `.github/agents/skeptic.agent.md`: adversarial synthesis reviewer.
- `.github/skills/*/SKILL.md`: named workflow procedures.
- `scripts/persona-lab`: calibration/lint harness.
- `scripts/check_study.py`: provenance/calibration gate.
- `scripts/export_synthesis.py`: gated Word export.

## Safety boundaries
- Never inspect `holdout/**` except through the calibration harness.
- Never use synthetic material as real evidence.
- Never force-add client-data paths to git.
- Keep committed examples fictional.
