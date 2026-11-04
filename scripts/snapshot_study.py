#!/usr/bin/env python3
"""Freeze the execution-time study configuration and persona validation profile."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research_os.application import FilesystemRepository, StudyService


def _read_metadata(repository, parent, identifier, filename):
    if (
        not isinstance(identifier, str)
        or not identifier
        or identifier in {".", ".."}
        or "/" in identifier
        or "\\" in identifier
    ):
        raise ValueError(f"invalid metadata identifier: {identifier!r}")
    path = f"{parent}/{identifier}/{filename}"
    return json.loads(repository.read_text(path))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="snapshot_study.py")
    parser.add_argument("study", help="study id under studies/")
    parser.add_argument("--client", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--limitation", action="append", required=True)
    args = parser.parse_args(argv)
    repository = FilesystemRepository(ROOT)
    try:
        config_path = f"studies/{args.study}/study.json"
        config = json.loads(repository.read_text(config_path))
        if not isinstance(config, dict):
            raise ValueError("study.json must contain a JSON object")
        method_meta = _read_metadata(
            repository, "methods", config["method"], "method.json"
        )
        output_meta = _read_metadata(
            repository, "outputs", config["output"], "contract.json"
        )
        snapshot = StudyService(repository).snapshot_execution(
            study_id=args.study,
            client_id=args.client,
            execution_provider=args.provider,
            execution_model=args.model,
            limitations=args.limitation,
            method_version=method_meta["version"],
            output_contract_version=output_meta["version"],
        )
    except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(snapshot, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
