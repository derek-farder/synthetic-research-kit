---
name: synthesize-study
description: Create provenance-preserving synthesis from real evidence and synthetic runs.
---
# synthesize-study
- Read the study question, protocol, hypotheses and all transcripts.
- Open-code into `coding.md`, recording themes with the runs and personas containing them. Code journey stage/process point only where the transcript or cited evidence supports it.
- Draft `synthesis.md` with these sections in order: Hypotheses; Single-persona observations; Surprises and misses; Validate with real people; Limits.
- Every hypothesis bullet ends with `[support: N runs / M personas]`.
- Every quote is a blockquote ending in `[SYN: runs/<file>.md]` (simulation) or `[REAL: E<n>]` (real evidence). Keep REAL and SYN material distinct, with supporting and counter-evidence.
- Under Limits, state each persona's validation status as `Calibration: <id>@<version>: <status>`.
- Avoid language that implies simulated output is real participant evidence or supports population quantities.
- Delegate the finished draft to the `skeptic` agent using only the study folder path.
- Correct or remove UNSUPPORTED hypotheses, explicitly flag WEAK ones, and retain unresolved objections under Limits.
- Run `python scripts/check_study.py studies/<study>` and fix all errors before completion.
