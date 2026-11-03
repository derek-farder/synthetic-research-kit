# Portability
Canonical methodology lives under `/skills/`. `.github/` and `.claude/` are platform adapters. Evidence, Audience, Insights, Validation, Research and Report engines are vendor-neutral.

## Adapter mapping
| Concept | Canonical | GitHub Copilot | Claude Code |
|---|---|---|---|
| Operating rules | `AGENTS.md`, `ARCHITECTURE.md` | `.github/copilot-instructions.md`, `.github/instructions/` | `.claude/CLAUDE.md` |
| Procedures | `skills/<name>/SKILL.md` | `.github/skills/<name>/SKILL.md` (thin wrapper) | `.claude/skills/<name>/SKILL.md` (thin wrapper) |
| Agents | - | `.github/agents/*.agent.md` | `.claude/agents/*.md` |
| File guardrails | `.gitignore`, `.githooks/`, scripts | none built in | `.claude/settings.json` deny rules |

Wrappers and agent bodies are kept identical across platforms; `tests/test_merge_safeguards.py` enforces it.

## Hardening
- Instruction files are behavioral guardrails, not a security boundary. Keep `.gitignore`, the pre-commit hook (`git config core.hooksPath .githooks`) and script gates as the mechanical controls.
- VS Code: verify `persona-runner`, `insights-analyst` and `skeptic` appear in the agent picker, and use Configure Tools if a listed tool name is not recognized. Keep persona-runner read-only; give skeptic only read/search/edit.
- Copilot tool names and enforcement vary by version; the validation harness is the only intended holdout consumer. Keep holdouts out of ordinary workspace context where practical and test holdout isolation on a fictional fixture before real data.
- If you add SDK or parallel delegation later, preserve exactly the same persona-runner information boundary.
