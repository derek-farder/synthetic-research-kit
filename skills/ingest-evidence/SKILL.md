---
name: ingest-evidence
description: Register and deterministically normalize new raw research sources.
---
# ingest-evidence
Inventory only new raw files in `clients/<client>/sources/raw/`; run `python scripts/ingest_sources.py clients/<client>` to create the ingestion batch, source entries and evidence records. Preserve explicit source/respondent/date/wave/context fields; never infer missing fields; never edit, rename or rewrite raw files (the script stops if a registered raw file has changed). Stop before analytical mapping.
