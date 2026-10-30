---
name: synthesize-study
description: Code synthetic transcripts, draft a provenance-preserving synthesis, obtain skeptic review, and pass the checker.
---
# Synthesize study
- Read the study question, protocol, hypotheses and all transcripts.
- Open-code into `coding.md`, recording themes with the runs and personas containing them.
- Draft `synthesis.md` with these sections in order: Hypotheses; Single-persona observations; Surprises and misses; Validate with real people; Limits.
- Every hypothesis bullet ends with `[support: N runs / M personas]`.
- Every quote is a blockquote ending in `[SYN: runs/<file>.md]` or `[REAL: E<n>]`.
- Avoid language that implies simulated output is real participant evidence or supports population quantities.
- Delegate the finished draft to the `skeptic` agent using only the study folder path.
- Correct or remove UNSUPPORTED hypotheses, explicitly flag WEAK ones, and retain unresolved objections under Limits.
- Run the provenance checker and fix all errors before completion.
