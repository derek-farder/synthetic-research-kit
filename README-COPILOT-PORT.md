# VS Code GitHub Copilot port

This overlay converts the AI-facing parts of the Synthetic Research Kit to VS Code GitHub Copilot conventions without replacing the portable Python scripts, formats, fixtures or git safeguards.

## Copy into the repository
Copy `AGENTS.md` and the `.github/` directory to the repository root. Keep the existing `scripts/`, `tools/persona-lab/`, templates, examples, `.gitignore`, `.githooks/`, `.gitattributes` and requirements from the reference build.

## VS Code mapping
- `CLAUDE.md` -> `.github/copilot-instructions.md` for repository-wide instructions, plus `AGENTS.md` for agent-facing repository context.
- `.claude/agents/*.md` -> `.github/agents/*.agent.md`.
- `.claude/skills/<name>/SKILL.md` -> `.github/skills/<name>/SKILL.md`.
- Claude permission settings do not map 1:1 to a guaranteed VS Code file-security boundary. Keep `.gitignore`, the pre-commit hook, and script-based gates as the mechanical controls. Treat Copilot read/write restrictions as guardrails unless you verify the installed VS Code/Copilot tool behavior.

## Important setup
1. Open the repository in a current VS Code with GitHub Copilot Chat enabled.
2. Verify `persona-runner` and `skeptic` appear in the Copilot agent selector.
3. Open each `.agent.md` and use VS Code's Configure Tools UI if a listed generic tool name is not recognized in your installed version. Keep persona-runner read-only; give skeptic only the minimum read/search/edit capability needed.
4. Ensure repository custom instructions are enabled.
5. Retain and enable the repository git hook with `git config core.hooksPath .githooks`.
6. Run the existing fictional acceptance suite before client data is added.
7. Test holdout isolation explicitly. The instruction files must not be treated as a security boundary.

## Recommended VS Code hardening
The reference design relies on a deny rule for `holdout/**`. Because Copilot tool names and enforcement can vary by environment/version, do not assume the Claude permission configuration ports directly. Use the existing harness as the only intended consumer of holdout data, keep holdouts out of ordinary workspace context where practical, and verify behavior in a fictional fixture before real data.

## Orchestration
Use the normal Copilot chat/agent session as the researcher/orchestrator. Invoke the specialist custom agents when their scope matches. The persona-runner remains stateless and blind. If you use SDK/Fleet-based parallel delegation later, preserve exactly the same information boundary.
