---
name: version-persona
description: Promote an approved persona proposal to an immutable new version.
---
# version-persona
Require explicit approval and complete reasoning/evidence delta (evidence added, qualifiers, contradictions, claims changed). Promote with `python scripts/promote_persona_version.py clients/<client> <proposal.json>`; it refuses unapproved proposals, missing change records and existing versions. Preserve prior version and validation history. New version starts not-run/stale for validation. Studies pin exact versions.
