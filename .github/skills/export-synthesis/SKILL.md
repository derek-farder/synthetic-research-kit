---
name: export-synthesis
description: Export a checked and skeptic-reviewed synthesis to Word using the repository exporter.
---
# Export synthesis
- Require `synthesis.md` and `skeptic-review.md`.
- Run the repository export script against the study folder. It must invoke the checker first.
- If checking fails, fix the Markdown source and export again. Never hand-edit the generated Word document.
- Do not use an unreviewed override unless the user explicitly requests it.
- Report the output path, exporter verification result and meaningful checker warnings.
- Remind the user to distribute the file only through the engagement's approved channel.
