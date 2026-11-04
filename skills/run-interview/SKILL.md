---
name: run-interview
description: Run approved interview turns with the blind Persona Runner.
---
# run-interview
- Require `status: approved` in the study protocol.
- Before the first Persona Runner call, create the immutable execution snapshot with `python scripts/snapshot_study.py <study-id> --client <client-id> --provider <provider> --model <deployment> --limitation "<limitation>"` (repeat `--limitation` for each material limitation). Use the actual approved execution provider/model and limitations from the approved protocol; if provider/model is unknown, stop rather than inventing it. Snapshot creation records the persona hashes and validation profiles and transitions the study to `status: running`.
- Use only the persona versions pinned in `study.json`: `clients/<client>/personas/versions/<id>/<version>.md`.
- For every persona-runner call, pass only: persona file path, transcript so far (or `(none)`), and next question.
- Do not pass study purpose, hypotheses, other personas' answers, insights, intended conclusions or researcher preferences.
- Apply run framing by changing interviewer wording, never by telling the persona agent what framing is being used.
- Ask core questions in order. Use protocol follow-ups where warranted and include the contradiction probe at least once per interview.
- Do not clean, merge or rewrite persona answers. Re-ask a broken answer once and record the retry.
- Save each run as `runs/<id>-r<n>.md` with frontmatter `synthetic: true`, `persona`, `persona_version`, `run`, `framing`, `protocol`, and the SYNTHETIC TRANSCRIPT notice; then run `python scripts/check_study.py studies/<study>`.
- Mark the study `status: complete` only after all planned runs are saved and the checker passes. Do not edit or recreate the execution snapshot.
- Report transcript count, turn count, retries and mechanical anomalies. Do not synthesize content during this step.
