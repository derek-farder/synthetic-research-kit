---
name: export-synthesis
description: Export a checked and skeptic-reviewed synthesis to Word using the repository exporter.
---
# export-synthesis
- Require `synthesis.md` and `skeptic-review.md`.
- Run `python scripts/export_synthesis.py studies/<study>` (add `--client clients/<client>` for a legacy study without `study.json`). It invokes the checker first.
- If checking fails, fix the Markdown source and export again. Never hand-edit the generated Word document.
- Do not use `--allow-unreviewed` unless the user explicitly requests it.
- Report the output path, exporter verification result and meaningful checker warnings.
- The export is a labeled working document ("SIMULATED RESEARCH - HYPOTHESES, NOT FINDINGS"). Client-ready deliverables go through `build-research-report`.
- Remind the user to distribute the file only through the engagement's approved channel.
