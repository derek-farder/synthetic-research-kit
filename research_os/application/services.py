"""Thin domain services over repository interfaces."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .repositories import Repository


def _json(repo: Repository, path: str) -> dict[str, Any]:
    data = json.loads(repo.read_text(path))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _safe_id(value: str) -> str:
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError("identifier must be a non-empty path component")
    return value


class ClientService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def get(self, client_id: str) -> dict[str, Any]:
        return _json(self.repository, f"clients/{_safe_id(client_id)}/client.json")

    def list(self) -> list[dict[str, Any]]:
        clients = []
        for path in self.repository.list_files("clients"):
            if path.endswith("/client.json") and "/_template/" not in path:
                clients.append(_json(self.repository, path))
        return clients


class EvidenceService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def records(self, client_id: str) -> list[dict[str, Any]]:
        client = _safe_id(client_id)
        path = f"clients/{client}/evidence/evidence.jsonl"
        if not self.repository.exists(path):
            return []
        return [
            json.loads(line)
            for line in self.repository.read_text(path).splitlines()
            if line.strip()
        ]


class PersonaService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def registry(self, client_id: str) -> dict[str, Any]:
        return _json(
            self.repository,
            f"clients/{_safe_id(client_id)}/personas/persona-registry.json",
        )

    def version(self, client_id: str, persona_id: str, version: str) -> str:
        return self.repository.read_text(
            f"clients/{_safe_id(client_id)}/personas/versions/"
            f"{_safe_id(persona_id)}/{_safe_id(version)}.md"
        )


class InsightService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def registry(self, client_id: str) -> dict[str, Any]:
        return _json(
            self.repository,
            f"clients/{_safe_id(client_id)}/insights/insight-registry.json",
        )


class ValidationService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def result(self, client_id: str, persona_id: str, version: str, run_id: str) -> dict[str, Any]:
        path = (
            f"clients/{_safe_id(client_id)}/validation/{_safe_id(persona_id)}/"
            f"{_safe_id(version)}/{_safe_id(run_id)}/results.json"
        )
        return _json(self.repository, path)


class StudyService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def configuration(self, study_id: str) -> dict[str, Any]:
        return _json(self.repository, f"studies/{_safe_id(study_id)}/study.json")

    def snapshot_execution(
        self,
        *,
        study_id: str,
        client_id: str,
        execution_provider: str,
        execution_model: str,
        limitations: list[str],
        method_version: str,
        output_contract_version: str,
    ) -> dict[str, Any]:
        study_id = _safe_id(study_id)
        client_id = _safe_id(client_id)
        study_path = f"studies/{study_id}/study.json"
        config = _json(self.repository, study_path)
        if config.get("client") != client_id:
            raise ValueError("study client does not match requested client")
        if config.get("execution_snapshot") is not None:
            raise ValueError("execution snapshot is immutable once created")
        if config.get("status") != "approved":
            raise ValueError("study must be approved before execution snapshot")
        if (
            not isinstance(execution_provider, str)
            or not execution_provider.strip()
            or not isinstance(execution_model, str)
            or not execution_model.strip()
        ):
            raise ValueError("execution provider and model are required")
        if (
            not isinstance(limitations, list)
            or not limitations
            or any(not isinstance(item, str) or not item.strip() for item in limitations)
        ):
            raise ValueError("study limitations must be explicitly recorded")
        for label, value in (
            ("method version", method_version),
            ("output contract version", output_contract_version),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} is required")
        for key in ("method", "output"):
            if not isinstance(config.get(key), str) or not config[key].strip():
                raise ValueError(f"study {key} is required for an execution snapshot")
        runs_per_persona = config.get("runs_per_persona")
        if type(runs_per_persona) is not int or runs_per_persona < 1:
            raise ValueError("study must configure at least one run per persona")

        registry_path = f"clients/{client_id}/personas/persona-registry.json"
        registry = _json(self.repository, registry_path)
        registered_personas = registry.get("personas")
        if not isinstance(registered_personas, list) or any(
            not isinstance(item, dict) or not isinstance(item.get("id"), str)
            for item in registered_personas
        ):
            raise ValueError("persona registry must contain a personas list")
        persona_entries = {item["id"]: item for item in registered_personas}
        pinned_personas = config.get("personas")
        if not isinstance(pinned_personas, list) or any(
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not isinstance(item.get("version"), str)
            for item in pinned_personas
        ):
            raise ValueError("study must pin personas by id and version")
        persona_snapshots = []
        for pinned in pinned_personas:
            persona_id = _safe_id(pinned["id"])
            version_id = _safe_id(str(pinned["version"]))
            entry = persona_entries.get(persona_id)
            if entry is None:
                raise ValueError(f"persona {persona_id} missing from client registry")
            version = next(
                (item for item in entry.get("versions", []) if str(item["version"]) == version_id),
                None,
            )
            if version is None:
                raise ValueError(f"persona version {persona_id}@{version_id} is not registered")
            persona_path = (
                f"clients/{client_id}/{version['file']}"
                if not str(version["file"]).startswith("clients/")
                else str(version["file"])
            )
            persona_bytes = self.repository.read_bytes(persona_path)
            persona_hash = hashlib.sha256(persona_bytes).hexdigest()
            if version.get("sha256") and version["sha256"] != persona_hash:
                raise ValueError(f"persona hash mismatch for {persona_id}@{version_id}")
            validation_profile = {
                "aggregate_status": version.get("validation_status", "not-run"),
                "dimensions": json.loads(
                    json.dumps(version.get("validation_dimensions", {}))
                ),
            }
            persona_snapshots.append(
                {
                    "id": persona_id,
                    "version": version_id,
                    "sha256": persona_hash,
                    "validation_profile": validation_profile,
                }
            )
        if not persona_snapshots:
            raise ValueError("study must pin at least one persona")
        snapshot = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "personas": persona_snapshots,
            "method": {"id": config.get("method"), "version": method_version},
            "output_contract": {
                "id": config.get("output"),
                "version": output_contract_version,
            },
            "execution": {
                "provider": execution_provider,
                "model": execution_model,
            },
            "runs_per_persona": runs_per_persona,
            "limitations": list(limitations),
        }
        config["study_format_version"] = "3.1"
        config["status"] = "running"
        config["execution_snapshot"] = snapshot
        self.repository.write_text(
            study_path, json.dumps(config, indent=2) + "\n"
        )
        return snapshot


class ReportService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def read(self, study_id: str, report_name: str = "research-report.md") -> str:
        return self.repository.read_text(
            f"studies/{_safe_id(study_id)}/{_safe_id(report_name)}"
        )

    def write(self, study_id: str, report: str, report_name: str = "research-report.md") -> None:
        self.repository.write_text(
            f"studies/{_safe_id(study_id)}/{_safe_id(report_name)}", report
        )
