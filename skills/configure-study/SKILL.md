---
name: configure-study
description: Configure a study from client, method, report output, and exact persona versions.
---
# configure-study
Create the study with `python scripts/new_study.py <study-id>` and set `study.json` (`schemas/study.schema.json`): client, method from `methods/`, output from `outputs/`, personas as exact `{id, version}` pairs from the client's persona registry (never "latest"), and `runs_per_persona`. Resolve configuration and validation states, create draft planning files, and stop for human approval. The approved protocol must record limitations for the execution snapshot. Never read holdout.
