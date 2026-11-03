# Claude Code Adapter
Read `/AGENTS.md` and `/ARCHITECTURE.md`; the full operating rules are in `/.github/copilot-instructions.md` and apply here unchanged. Canonical procedures live under `/skills/`; `.claude/skills/` only points to them. Holdout is validation-only. Raw sources are immutable. Persona/insight changes require reviewed proposals. Preserve provenance and never present synthetic output as research evidence.

`.claude/settings.json` denies Read on holdout and Edit on raw sources for Claude's file tools. That is a guardrail, not a security boundary: shell commands are not covered, so never use them to work around it.
