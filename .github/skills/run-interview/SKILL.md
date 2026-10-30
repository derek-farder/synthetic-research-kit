---
name: run-interview
description: Run an approved synthetic interview protocol through the blind persona-runner agent and save untouched transcripts.
---
# Run interview
- Require `status: approved` in the study protocol.
- For every persona-runner call, pass only: persona file path, transcript so far (or `(none)`), and next question.
- Do not pass study purpose, hypotheses, other personas' answers, intended conclusions or researcher preferences.
- Apply run framing by changing interviewer wording, never by telling the persona agent what framing is being used.
- Ask core questions in order. Use protocol follow-ups where warranted and include the contradiction probe at least once per interview.
- Do not clean, merge or rewrite persona answers. Re-ask a broken answer once and record the retry.
- Save each run using the repository transcript format, then run `scripts/check_study.py <study>`.
- Report transcript count, turn count, retries and mechanical anomalies. Do not synthesize content during this step.
