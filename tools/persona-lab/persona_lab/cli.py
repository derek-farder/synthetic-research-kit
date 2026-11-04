from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path

from .core import holdouts, leakage, lint_persona, load_evidence, load_persona
from .models import (
    ModelConfig,
    ModelConfigurationError,
    ModelRequestError,
    create_chat_model,
    load_model_config,
)
from .validation import (
    HARNESS_VERSION,
    VALID_DIMENSIONS,
    ValidationInputError,
    mark_holdout_contaminated,
    run_backtest,
    run_behavioral_dimension,
)
from .validation import JudgeOutputError


class _MockModel:
    def __init__(self, judge: bool = False):
        self.judge = judge

    def complete(self, messages, *, temperature=0.0, max_tokens=1024):
        if self.judge:
            return json.dumps(
                {"verdict": "WARN", "rationale": "Mock plumbing response; not evaluated."}
            )
        return "Mock generated response; not persona evidence."


def _client_id(persona_path: Path) -> str | None:
    for parent in persona_path.parents:
        config = parent / "client.json"
        if config.exists():
            try:
                client_config = json.loads(config.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValidationInputError(
                    f"cannot read client metadata at {config}: {exc}"
                ) from exc
            if not isinstance(client_config, dict):
                raise ValidationInputError(
                    f"client metadata at {config} must contain a JSON object"
                )
            client_id = client_config.get("client_id")
            if not isinstance(client_id, str) or not client_id.strip():
                raise ValidationInputError(
                    f"client metadata at {config} requires a non-empty client_id"
                )
            return client_id
    return None


def _update_live_profile(
    persona_path: Path,
    *,
    dimension: str,
    result: dict,
    result_path: Path,
) -> None:
    """Append a live dimension result to the matching immutable-version registry entry."""
    for parent in persona_path.parents:
        registry_path = parent / "personas" / "persona-registry.json"
        if not registry_path.exists():
            continue
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("personas"), list):
            raise ValidationInputError(
                f"persona registry at {registry_path} must contain a personas list"
            )
        persona_id = result["metadata"]["persona_id"]
        persona_version = result["metadata"]["persona_version"]
        expected_hash = result["metadata"]["persona_sha256"]
        entry = next(
            (
                item for item in data["personas"]
                if isinstance(item, dict) and item.get("id") == persona_id
            ),
            None,
        )
        if entry is None:
            raise ValidationInputError(f"persona {persona_id} missing from registry")
        version = next(
            (
                item for item in entry.get("versions", [])
                if isinstance(item, dict)
                and str(item.get("version")) == persona_version
            ),
            None,
        )
        if version is None:
            raise ValidationInputError(
                f"persona version {persona_id}@{persona_version} missing from registry"
            )
        if version.get("sha256") != expected_hash:
            raise ValidationInputError(
                f"registry hash does not match immutable persona {persona_id}@{persona_version}"
            )
        validation_runs = version.setdefault("validation_runs", [])
        validation_dimensions = version.setdefault("validation_dimensions", {})
        if not isinstance(validation_runs, list) or not isinstance(
            validation_dimensions, dict
        ):
            raise ValidationInputError(
                f"validation profile for {persona_id}@{persona_version} is malformed"
            )
        record = {
            "dimension": dimension,
            "status": result["status"],
            "persona_sha256": expected_hash,
            "result_file": str(result_path.resolve()),
            "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "provider": result["metadata"]["provider"],
            "persona_model": result["metadata"]["persona_model"],
            "judge_provider": result["metadata"]["judge_provider"],
            "judge_model": result["metadata"]["judge_model"],
            "persona_prompt_version": result["metadata"]["persona_prompt_version"],
            "judge_prompt_version": result["metadata"]["judge_prompt_version"],
            "rubric_version": result["metadata"]["rubric_version"],
            "probe_version": result["metadata"]["probe_version"],
            "harness_version": result["metadata"]["harness_version"],
            "generation_parameters": result["metadata"]["generation_parameters"],
        }
        validation_runs.append(record)
        validation_dimensions[dimension] = record
        registry_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return
    raise ValidationInputError(
        "no persona registry found for the live validation result"
    )


def _write_result(out: Path, result: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    result_path = out / "results.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (out / "report.md").write_text(
        "\n".join(
            [
                f'# {result["status"]} — {result["metadata"]["dimension"]}',
                "",
                "This is a dimension-specific result; it is not an overall validity score.",
                "",
                f'- Persona: `{result["metadata"]["persona_id"]}@{result["metadata"]["persona_version"]}`',
                f'- Persona SHA-256: `{result["metadata"]["persona_sha256"]}`',
                f'- Persona model: `{result["metadata"]["provider"]}/{result["metadata"]["persona_model"]}`',
                f'- Judge model: `{result["metadata"]["judge_provider"]}/{result["metadata"]["judge_model"]}`',
                f'- Persona prompt: `{result["metadata"]["persona_prompt_version"]}`',
                f'- Judge prompt: `{result["metadata"]["judge_prompt_version"]}`',
                f'- Rubric: `{result["metadata"]["rubric_version"]}`',
                f'- Probe: `{result["metadata"]["probe_version"]}`',
                f'- Harness: `{result["metadata"]["harness_version"]}`',
                f'- Generation parameters: `{json.dumps(result["metadata"]["generation_parameters"], sort_keys=True)}`',
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_leakage(out: Path, persona_path: Path, persona: dict, evidence: dict, holdout_path: str) -> int:
    hs = holdouts(holdout_path, persona["meta"].get("id"))
    if not hs:
        print("ERROR: no holdout interviews found for persona")
        return 2
    leaks = leakage(evidence, hs)
    status = "INVALID" if leaks else "PASS"
    result = {
        "meta": {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "persona_id": persona["meta"].get("id"),
            "persona_version": persona["meta"].get("version"),
            "persona_path": str(persona_path.resolve()),
            "persona_sha256": hashlib.sha256(persona_path.read_bytes()).hexdigest(),
            "harness_version": HARNESS_VERSION,
            "mock": False,
            "live_models_used": False,
            "deterministic": True,
        },
        "dimensions": {
            "grounding": "NOT-RUN",
            "leakage": status,
            "backtest": "NOT-RUN",
            "coherence": "NOT-RUN",
            "abstention": "NOT-RUN",
            "framing_resistance": "NOT-RUN",
            "distinctiveness": "NOT-RUN",
        },
        "leakage": {
            "holdout_records": len(hs),
            "leak_count": len(leaks),
            "matches": leaks,
        },
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        f"# Leakage: {status}",
        "",
        "This deterministic check only tests source/holdout overlap. It is not a persona behavioral validation.",
        "",
        f'- Persona: `{result["meta"]["persona_id"]}@{result["meta"]["persona_version"] or "unversioned"}`',
        f'- Persona SHA-256: `{result["meta"]["persona_sha256"]}`',
        f"- Holdout records processed inside the harness: {len(hs)}",
        f"- Detected leakage matches: {len(leaks)}",
        "- Backtest, coherence, abstention, framing resistance and distinctiveness: NOT-RUN",
    ]
    if leaks:
        lines += ["", "## Leakage references"] + [f"- `{item}`" for item in leaks]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)
    return 2 if leaks else 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="persona-lab")
    sub = parser.add_subparsers(dest="cmd", required=True)
    commands = ("lint", "leakage", *sorted(VALID_DIMENSIONS), "contaminate-holdout")
    for name in commands:
        command = sub.add_parser(name)
        if name == "contaminate-holdout":
            command.add_argument("--ledger", required=True)
            command.add_argument("--holdout-id", required=True)
            command.add_argument("--approach-hash", required=True)
            command.add_argument("--reason", required=True)
            continue
        command.add_argument("--persona", required=True)
        command.add_argument("--evidence", required=True)
        command.add_argument("--out", required=True)
        command.add_argument("--mock", action="store_true")
        command.add_argument("--model")
        command.add_argument("--judge-model")
        command.add_argument("--study-id")
        command.add_argument("--client-id")
        command.add_argument("--telemetry-path")
        if name == "leakage":
            command.add_argument("--holdout", required=True)
        elif name == "lint":
            pass
        elif name == "backtest":
            command.add_argument("--holdout", required=True)
            command.add_argument("--comparison-design", required=True)
            command.add_argument("--approach-hash", required=True)
            command.add_argument("--contamination-ledger", required=True)
            command.add_argument("--temperature", type=float, default=0.0)
            command.add_argument("--max-tokens", type=int, default=1024)
        else:
            command.add_argument("--probes", required=True)
            command.add_argument("--others", nargs="*", default=[])
            command.add_argument("--temperature", type=float, default=0.0)
            command.add_argument("--max-tokens", type=int, default=1024)
    args = parser.parse_args(argv)

    if args.cmd == "contaminate-holdout":
        try:
            mark_holdout_contaminated(
                ledger_path=args.ledger,
                holdout_id=args.holdout_id,
                revised_approach_hash=args.approach_hash,
                reason=args.reason,
            )
        except ValidationInputError as exc:
            print(f"ERROR: {exc}")
            return 2
        print("Recorded holdout contamination.")
        return 0

    persona_path = Path(args.persona)
    out = Path(args.out)
    try:
        persona = load_persona(persona_path)
        evidence = load_evidence(args.evidence)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    if args.cmd == "leakage":
        return _write_leakage(out, persona_path, persona, evidence, args.holdout)
    if args.cmd == "lint":
        issues, scores = lint_persona(persona, evidence)
        tests = {f"lint.{key}": value for key, value in scores.items()}
        verdicts = {
            "lint.errors": "PASS" if scores["errors"] == 0 else "FAIL",
            "lint.grounded": (
                "PASS" if scores["grounded"] >= 0.9
                else "WARN" if scores["grounded"] >= 0.7
                else "FAIL"
            ),
            "lint.thick": (
                "PASS" if scores["thick"] >= 0.6
                else "WARN" if scores["thick"] >= 0.4
                else "FAIL"
            ),
        }
        result = {
            "meta": {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "persona_id": persona["meta"].get("id"),
                "persona_version": persona["meta"].get("version"),
                "persona_sha256": hashlib.sha256(persona_path.read_bytes()).hexdigest(),
                "mock": False,
            },
            "tests": tests,
            "verdicts": verdicts,
            "sections": {"lint_issues": issues},
            "overall": (
                "FAIL" if "FAIL" in verdicts.values()
                else "WARN" if "WARN" in verdicts.values()
                else "PASS"
            ),
        }
        out.mkdir(parents=True, exist_ok=True)
        (out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
        (out / "report.md").write_text(
            "# Persona grounding lint\n\n"
            + "\n".join(f"- {key}: {value}" for key, value in verdicts.items())
            + "\n",
            encoding="utf-8",
        )
        print(result["overall"])
        return 1 if result["overall"] == "FAIL" else 0

    dimension = "backtest" if args.cmd == "backtest" else args.cmd
    try:
        if args.mock:
            persona_config = ModelConfig(
                role="persona", provider="mock", model="mock-persona",
                endpoint="", api_version="", auth_method="", credential_env="",
                credential="",
            )
            judge_config = ModelConfig(
                role="judge", provider="mock", model="mock-judge",
                endpoint="", api_version="", auth_method="", credential_env="",
                credential="",
            )
            persona_model, judge_model = _MockModel(), _MockModel(judge=True)
        else:
            persona_config = load_model_config("persona", args.model)
            judge_config = load_model_config("judge", args.judge_model)
            persona_model = create_chat_model(persona_config)
            judge_model = create_chat_model(judge_config)
        telemetry_path = args.telemetry_path or str(out / "telemetry.jsonl")
        persona_id = persona["meta"].get("id")
        persona_version = str(persona["meta"].get("version") or "")
        client_id = args.client_id or _client_id(persona_path)
        if dimension == "backtest":
            result = run_backtest(
                persona_path=persona_path,
                holdout_path=args.holdout,
                comparison_design_path=args.comparison_design,
                persona_model=persona_model,
                persona_config=persona_config,
                judge_model=judge_model,
                judge_config=judge_config,
                telemetry_path=telemetry_path,
                contamination_ledger_path=args.contamination_ledger,
                persona_id=persona_id,
                persona_version=persona_version,
                study_id=args.study_id,
                client_id=client_id,
                approach_hash=args.approach_hash,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
        else:
            result = run_behavioral_dimension(
                dimension=dimension,
                persona_path=persona_path,
                probe_path=args.probes,
                persona_model=persona_model,
                persona_config=persona_config,
                judge_model=judge_model,
                judge_config=judge_config,
                telemetry_path=telemetry_path,
                persona_id=persona_id,
                persona_version=persona_version,
                study_id=args.study_id,
                client_id=client_id,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                other_persona_paths=args.others,
            )
    except (
        ValidationInputError,
        ModelConfigurationError,
        ModelRequestError,
        JudgeOutputError,
    ) as exc:
        print(f"ERROR: {exc}")
        return 2

    if args.mock:
        result["status"] = "MOCK"
        result["mock"] = True
        result["metadata"]["mock"] = True
        for case in result["cases"]:
            case.pop("verdict", None)
            case.pop("rationale", None)
    else:
        result["metadata"]["mock"] = False
    _write_result(out, result)
    if not args.mock:
        try:
            _update_live_profile(
                persona_path,
                dimension=dimension,
                result=result,
                result_path=out / "results.json",
            )
        except (OSError, json.JSONDecodeError, ValidationInputError) as exc:
            print(f"ERROR: live result saved, but registry profile update failed: {exc}")
            return 2
    print(result["status"])
    return 0 if result["status"] in {"PASS", "MOCK"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
