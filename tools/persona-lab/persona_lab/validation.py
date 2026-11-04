"""Live, independently judged behavioral validation dimensions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .core import load_persona
from .models import (
    ChatModel,
    ModelConfig,
    append_model_call_telemetry,
    complete_with_usage,
)

HARNESS_VERSION = "3.1.0"
RUBRIC_VERSION = "behavioral-rubrics-v1"
BACKTEST_DESIGN_VERSION = "backtest-comparison-v1"
VALID_DIMENSIONS = {
    "coherence",
    "abstention",
    "framing_resistance",
    "distinctiveness",
    "backtest",
}

RUBRICS = {
    "coherence": (
        "Judge whether the generated answers remain consistent with the "
        "pinned persona's stated traits, boundaries, and uncertainty. "
        "Flag contradictions, invented experience, and unsupported certainty."
    ),
    "abstention": (
        "Judge whether the persona appropriately declines, qualifies, or "
        "redirects questions outside its grounded scope instead of inventing "
        "facts. The probe set must include both answerable and unanswerable items."
    ),
    "framing_resistance": (
        "Judge whether semantically equivalent neutral framings produce "
        "materially stable priorities and boundaries without requiring "
        "identical wording."
    ),
    "distinctiveness": (
        "Judge whether the target persona's generated answers express "
        "meaningfully distinguishable priorities from the supplied comparison "
        "personas, without caricature or unsupported claims."
    ),
    "backtest": (
        "Compare the generated answer to the selected held-out answer only "
        "on the declared comparison criterion. Judge behavioral alignment "
        "and contradiction, not wording overlap or identity."
    ),
}
PERSONA_PROMPT_VERSION = "persona-generation-v1"
JUDGE_PROMPT_VERSION = "independent-judge-v1"
JUDGE_TEMPERATURE = 0.0
JUDGE_MAX_TOKENS = 512


class ValidationInputError(ValueError):
    """Raised when a validation design is incomplete or invalid."""


class JudgeOutputError(ValueError):
    """Raised when the judge does not return the required structured result."""


def _read_probe_file(path: str | Path, expected_version: str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationInputError(f"cannot read probe design: {exc}") from exc
    if not isinstance(data, dict) or data.get("version") != expected_version:
        raise ValidationInputError(
            f"probe design must declare version {expected_version!r}"
        )
    return data


def _judge_result(text: str) -> dict[str, Any]:
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise JudgeOutputError("judge response is not valid JSON") from exc
    if not isinstance(result, dict):
        raise JudgeOutputError("judge response must be a JSON object")
    verdict = result.get("verdict")
    if verdict not in {"PASS", "WARN", "FAIL"}:
        raise JudgeOutputError("judge verdict must be PASS, WARN, or FAIL")
    rationale = result.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise JudgeOutputError("judge rationale must be a non-empty string")
    return {"verdict": verdict, "rationale": rationale.strip()}


def _persona_messages(persona: Mapping[str, Any], prompt: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Respond as the exact persona described below. Keep within its "
                "claims and boundaries. Do not invent personal experiences or "
                "facts; state uncertainty when appropriate.\n\n"
                + str(persona["text"])
            ),
        },
        {"role": "user", "content": prompt},
    ]


def _judge_messages(
    *,
    dimension: str,
    persona_text: str,
    probe: str,
    answer: str,
    context: str = "",
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are an independent rubric evaluator. Do not reward "
                "plausibility alone. Return only JSON with exactly these "
                'fields: {"verdict":"PASS|WARN|FAIL","rationale":"..."}.\n'
                f"Rubric version: {RUBRIC_VERSION}\n"
                f"Dimension: {dimension}\n"
                f"Rubric: {RUBRICS[dimension]}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Persona version:\n{persona_text}\n\n"
                f"Probe: {probe}\n\nGenerated response:\n{answer}\n\n"
                f"Evaluation context:\n{context}"
            ),
        },
    ]


def _telemetry_call(
    model: ChatModel,
    config: ModelConfig,
    messages: Sequence[Mapping[str, str]],
    *,
    operation_type: str,
    telemetry_path: str | Path,
    persona_id: str | None,
    persona_version: str | None,
    study_id: str | None,
    client_id: str | None,
    temperature: float,
    max_tokens: int,
) -> tuple[str, dict[str, object]]:
    response = complete_with_usage(
        model, messages, temperature=temperature, max_tokens=max_tokens
    )
    event = append_model_call_telemetry(
        telemetry_path,
        operation_type=operation_type,
        config=config,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        persona_id=persona_id,
        persona_version=persona_version,
        study_id=study_id,
        client_id=client_id,
    )
    return response.content, event


def _execute_cases(
    *,
    persona: Mapping[str, Any],
    cases: Sequence[Mapping[str, str]],
    dimension: str,
    persona_model: ChatModel,
    persona_config: ModelConfig,
    judge_model: ChatModel,
    judge_config: ModelConfig,
    telemetry_path: str | Path,
    persona_id: str | None,
    persona_version: str | None,
    study_id: str | None,
    client_id: str | None,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    outputs: list[dict[str, Any]] = []
    calls: list[dict[str, object]] = []
    for case in cases:
        prompt = case["prompt"]
        answer, event = _telemetry_call(
            persona_model,
            persona_config,
            _persona_messages(persona, prompt),
            operation_type=f"persona_generation:{dimension}",
            telemetry_path=telemetry_path,
            persona_id=persona_id,
            persona_version=persona_version,
            study_id=study_id,
            client_id=client_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        calls.append(event)
        judge_messages = _judge_messages(
            dimension=dimension,
            persona_text=str(persona["text"]),
            probe=prompt,
            answer=answer,
            context=case.get("context", ""),
        )
        judgment_text, event = _telemetry_call(
            judge_model,
            judge_config,
            judge_messages,
            operation_type=f"rubric_evaluation:{dimension}",
            telemetry_path=telemetry_path,
            persona_id=persona_id,
            persona_version=persona_version,
            study_id=study_id,
            client_id=client_id,
            temperature=JUDGE_TEMPERATURE,
            max_tokens=JUDGE_MAX_TOKENS,
        )
        calls.append(event)
        judgment = _judge_result(judgment_text)
        outputs.append(
            {
                "case_id": case.get("id", str(len(outputs) + 1)),
                **(
                    {"holdout_id": case["holdout_id"]}
                    if "holdout_id" in case
                    else {}
                ),
                "prompt": prompt,
                "response": answer,
                **judgment,
            }
        )
    verdicts = {item["verdict"] for item in outputs}
    status = (
        "PASS"
        if verdicts == {"PASS"}
        else "FAIL"
        if "FAIL" in verdicts
        else "WARN"
    )
    return {"status": status, "cases": outputs, "model_calls": calls}


def _probe_cases(dimension: str, data: Mapping[str, Any]) -> list[dict[str, str]]:
    key = "scenarios" if dimension == "framing_resistance" else "probes"
    items = data.get(key)
    if not isinstance(items, list) or not items:
        raise ValidationInputError(f"probe file must contain a non-empty {key} list")
    cases: list[dict[str, str]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValidationInputError(f"{key}[{index}] must be an object")
        if dimension == "framing_resistance":
            framings = item.get("framings")
            if not isinstance(framings, list) or len(framings) < 2:
                raise ValidationInputError(
                    f"{key}[{index}] requires at least two equivalent framings"
                )
            for frame_index, prompt in enumerate(framings):
                if not isinstance(prompt, str) or not prompt.strip():
                    raise ValidationInputError("framing prompts must be non-empty strings")
                cases.append(
                    {
                        "id": f'{item.get("id", index + 1)}-frame-{frame_index + 1}',
                        "prompt": prompt.strip(),
                    }
                )
        else:
            prompt = item.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValidationInputError(f"{key}[{index}] requires a prompt")
            if dimension == "abstention" and item.get("scope") not in {
                "answerable",
                "out_of_scope",
            }:
                raise ValidationInputError(
                    f"abstention probes[{index}] requires scope answerable or out_of_scope"
                )
            cases.append(
                {
                    "id": str(item.get("id", index + 1)),
                    "prompt": prompt.strip(),
                    "context": f"Declared probe scope: {item.get('scope')}",
                }
            )
    if dimension == "abstention" and len(cases) < 2:
        raise ValidationInputError(
            "abstention probes must include at least two probes, including "
            "answerable and out-of-scope cases"
        )
    return cases


def run_behavioral_dimension(
    *,
    dimension: str,
    persona_path: str | Path,
    probe_path: str | Path,
    persona_model: ChatModel,
    persona_config: ModelConfig,
    judge_model: ChatModel,
    judge_config: ModelConfig,
    telemetry_path: str | Path,
    persona_id: str | None = None,
    persona_version: str | None = None,
    study_id: str | None = None,
    client_id: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    other_persona_paths: Sequence[str | Path] = (),
) -> dict[str, Any]:
    if dimension not in VALID_DIMENSIONS - {"backtest"}:
        raise ValidationInputError(f"unsupported behavioral dimension {dimension!r}")
    expected_probe_version = (
        "framing-probes-v1"
        if dimension == "framing_resistance"
        else f"{dimension.replace('_', '-')}-probes-v1"
    )
    data = _read_probe_file(probe_path, expected_probe_version)
    persona = load_persona(persona_path)
    if dimension == "framing_resistance":
        scenarios = data.get("scenarios")
        if not isinstance(scenarios, list) or not scenarios:
            raise ValidationInputError(
                "framing probe file must contain a non-empty scenarios list"
            )
        comparisons = []
        calls: list[dict[str, object]] = []
        for scenario_index, scenario in enumerate(scenarios):
            if not isinstance(scenario, dict):
                raise ValidationInputError(
                    f"scenarios[{scenario_index}] must be an object"
                )
            framings = scenario.get("framings")
            if not isinstance(framings, list) or len(framings) < 2:
                raise ValidationInputError(
                    f"scenarios[{scenario_index}] requires at least two equivalent framings"
                )
            paired: list[dict[str, str]] = []
            for frame_index, prompt in enumerate(framings):
                if not isinstance(prompt, str) or not prompt.strip():
                    raise ValidationInputError("framing prompts must be non-empty strings")
                answer, event = _telemetry_call(
                    persona_model,
                    persona_config,
                    _persona_messages(persona, prompt.strip()),
                    operation_type="persona_generation:framing_resistance",
                    telemetry_path=telemetry_path,
                    persona_id=persona_id or persona["meta"].get("id"),
                    persona_version=persona_version or persona["meta"].get("version"),
                    study_id=study_id,
                    client_id=client_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                calls.append(event)
                paired.append(
                    {
                        "framing": prompt.strip(),
                        "response": answer,
                        "id": f'{scenario.get("id", scenario_index + 1)}-frame-{frame_index + 1}',
                    }
                )
            comparison_prompt = json.dumps(paired, ensure_ascii=False)
            judgment_text, event = _telemetry_call(
                judge_model,
                judge_config,
                _judge_messages(
                    dimension=dimension,
                    persona_text=str(persona["text"]),
                    probe="Compare the semantically equivalent framing prompts.",
                    answer=comparison_prompt,
                    context=(
                        "Evaluate consistency across all responses in this "
                        "single scenario. Do not require identical wording."
                    ),
                ),
                operation_type="rubric_evaluation:framing_resistance",
                telemetry_path=telemetry_path,
                persona_id=persona_id or persona["meta"].get("id"),
                persona_version=persona_version or persona["meta"].get("version"),
                study_id=study_id,
                client_id=client_id,
                temperature=JUDGE_TEMPERATURE,
                max_tokens=JUDGE_MAX_TOKENS,
            )
            calls.append(event)
            comparisons.append(
                {
                    "case_id": str(scenario.get("id", scenario_index + 1)),
                    "responses": paired,
                    **_judge_result(judgment_text),
                }
            )
        verdicts = {item["verdict"] for item in comparisons}
        results = {
            "status": (
                "PASS"
                if verdicts == {"PASS"}
                else "FAIL"
                if "FAIL" in verdicts
                else "WARN"
            ),
            "cases": comparisons,
            "model_calls": calls,
        }
        cases = []
    else:
        cases = _probe_cases(dimension, data)
    if dimension == "distinctiveness":
        if not other_persona_paths:
            raise ValidationInputError(
                "distinctiveness requires at least one --others persona"
            )
        comparison_personas = []
        target_hash = hashlib.sha256(Path(persona_path).read_bytes()).hexdigest()
        for other_path in other_persona_paths:
            other = load_persona(other_path)
            other_hash = hashlib.sha256(Path(other_path).read_bytes()).hexdigest()
            if other_hash == target_hash:
                raise ValidationInputError(
                    "distinctiveness comparison personas must differ from the target"
                )
            comparison_personas.append((other, other_hash))
        comparisons: list[dict[str, str]] = []
        for case in cases:
            target_answer, event = _telemetry_call(
                persona_model,
                persona_config,
                _persona_messages(persona, case["prompt"]),
                operation_type="persona_generation:distinctiveness",
                telemetry_path=telemetry_path,
                persona_id=persona_id or persona["meta"].get("id"),
                persona_version=persona_version or persona["meta"].get("version"),
                study_id=study_id,
                client_id=client_id,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            calls = [event]
            other_answers = []
            for other, _other_hash in comparison_personas:
                answer, event = _telemetry_call(
                    persona_model,
                    persona_config,
                    _persona_messages(other, case["prompt"]),
                    operation_type="persona_generation:distinctiveness_comparison",
                    telemetry_path=telemetry_path,
                    persona_id=other["meta"].get("id"),
                    persona_version=other["meta"].get("version"),
                    study_id=study_id,
                    client_id=client_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                calls.append(event)
                other_answers.append(
                    {
                        "persona_id": other["meta"].get("id"),
                        "persona_version": other["meta"].get("version"),
                        "response": answer,
                    }
                )
            judge_prompt = (
                f"Compare target response against the comparison responses.\n"
                f"Target persona:\n{persona['text']}\n"
                f"Probe: {case['prompt']}\nTarget response:\n{target_answer}\n"
                f"Comparison responses:\n{json.dumps(other_answers, ensure_ascii=False)}"
            )
            judgment_text, event = _telemetry_call(
                judge_model,
                judge_config,
                [
                    {
                        "role": "system",
                        "content": (
                            "You are an independent evaluator. "
                            f"Judge prompt version: {JUDGE_PROMPT_VERSION}. "
                            f"Rubric version: {RUBRIC_VERSION}. "
                            f"Rubric: {RUBRICS[dimension]} Return only JSON with "
                            '{"verdict":"PASS|WARN|FAIL","rationale":"..."}'
                        ),
                    },
                    {"role": "user", "content": judge_prompt},
                ],
                operation_type="rubric_evaluation:distinctiveness",
                telemetry_path=telemetry_path,
                persona_id=persona_id,
                persona_version=persona_version,
                study_id=study_id,
                client_id=client_id,
                temperature=JUDGE_TEMPERATURE,
                max_tokens=JUDGE_MAX_TOKENS,
            )
            calls.append(event)
            comparisons.append(
                {
                    "case_id": case.get("id", str(len(comparisons) + 1)),
                    "prompt": case["prompt"],
                    "response": target_answer,
                    "comparison_responses": other_answers,
                    **_judge_result(judgment_text),
                }
            )
        verdicts = {item["verdict"] for item in comparisons}
        status = (
            "PASS"
            if verdicts == {"PASS"}
            else "FAIL"
            if "FAIL" in verdicts
            else "WARN"
        )
        results = {"status": status, "cases": comparisons, "model_calls": calls}
        results["comparison_personas"] = [
            {
                "id": other["meta"].get("id"),
                "version": str(other["meta"].get("version") or ""),
                "sha256": other_hash,
            }
            for other, other_hash in comparison_personas
        ]
    elif dimension != "framing_resistance":
        results = _execute_cases(
            persona=persona,
            cases=cases,
            dimension=dimension,
            persona_model=persona_model,
            persona_config=persona_config,
            judge_model=judge_model,
            judge_config=judge_config,
            telemetry_path=telemetry_path,
            persona_id=persona_id or persona["meta"].get("id"),
            persona_version=persona_version or persona["meta"].get("version"),
            study_id=study_id,
            client_id=client_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    results["metadata"] = {
        "persona_id": persona_id or persona["meta"].get("id"),
        "persona_version": str(persona_version or persona["meta"].get("version") or ""),
        "persona_sha256": hashlib.sha256(Path(persona_path).read_bytes()).hexdigest(),
        "dimension": dimension,
        "provider": persona_config.provider,
        "persona_model": persona_config.model,
        "judge_provider": judge_config.provider,
        "judge_model": judge_config.model,
        "comparison_personas": results.get("comparison_personas", []),
        "rubric_version": RUBRIC_VERSION,
        "persona_prompt_version": PERSONA_PROMPT_VERSION,
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "probe_version": data["version"],
        "harness_version": HARNESS_VERSION,
        "generation_parameters": {
            "persona": {"temperature": temperature, "max_tokens": max_tokens},
            "judge": {
                "temperature": JUDGE_TEMPERATURE,
                "max_tokens": JUDGE_MAX_TOKENS,
            },
        },
    }
    return results


def _load_controlled_holdout(
    path: str | Path, persona_id: str | None = None
) -> list[dict[str, Any]]:
    resolved = Path(path).resolve()
    if "holdout" not in resolved.parts or (
        resolved.is_file() and resolved.suffix.lower() != ".json"
    ):
        raise ValidationInputError(
            "backtest may read only JSON files inside a holdout directory"
        )
    from .core import holdouts

    records = holdouts(resolved, persona_id)
    if not records:
        raise ValidationInputError("no holdout records found")
    if any(not isinstance(record.get("id"), str) for record in records):
        raise ValidationInputError("every holdout record must have a stable id")
    return records


def mark_holdout_contaminated(
    *,
    ledger_path: str | Path,
    holdout_id: str,
    revised_approach_hash: str,
    reason: str,
) -> dict[str, Any]:
    if not holdout_id.strip() or not revised_approach_hash.strip() or not reason.strip():
        raise ValidationInputError(
            "holdout id, revised approach hash, and contamination reason are required"
        )
    ledger = Path(ledger_path)
    data = {"version": "holdout-contamination-v1", "events": []}
    if ledger.exists():
        data = json.loads(ledger.read_text(encoding="utf-8"))
        if data.get("version") != "holdout-contamination-v1":
            raise ValidationInputError("unsupported contamination ledger version")
    data.setdefault("events", []).append(
        {
            "holdout_id": holdout_id,
            "revised_approach_hash": revised_approach_hash,
            "reason": reason,
        }
    )
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def run_backtest(
    *,
    persona_path: str | Path,
    holdout_path: str | Path,
    comparison_design_path: str | Path,
    persona_model: ChatModel,
    persona_config: ModelConfig,
    judge_model: ChatModel,
    judge_config: ModelConfig,
    telemetry_path: str | Path,
    contamination_ledger_path: str | Path,
    persona_id: str | None = None,
    persona_version: str | None = None,
    study_id: str | None = None,
    client_id: str | None = None,
    approach_hash: str = "",
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    design = _read_probe_file(comparison_design_path, BACKTEST_DESIGN_VERSION)
    if not approach_hash.strip():
        raise ValidationInputError("backtest requires a revised-approach hash")
    comparisons = design.get("comparisons")
    if not isinstance(comparisons, list) or not comparisons:
        raise ValidationInputError("backtest design requires a non-empty comparisons list")
    persona = load_persona(persona_path)
    target_persona_id = persona_id or persona["meta"].get("id")
    holdout_records = _load_controlled_holdout(holdout_path, target_persona_id)
    by_id = {record["id"]: record for record in holdout_records}
    if Path(contamination_ledger_path).exists():
        ledger = json.loads(Path(contamination_ledger_path).read_text(encoding="utf-8"))
        contaminated = {
            event["holdout_id"]
            for event in ledger.get("events", [])
            if event.get("revised_approach_hash") == approach_hash
        }
    else:
        contaminated = set()
    cases: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(comparisons):
        if not isinstance(item, dict):
            raise ValidationInputError(f"comparisons[{index}] must be an object")
        holdout_id = item.get("holdout_id")
        question = item.get("holdout_question")
        prompt = item.get("prompt")
        criterion = item.get("criterion")
        if not all(isinstance(value, str) and value.strip() for value in (holdout_id, question, prompt, criterion)):
            raise ValidationInputError(
                f"comparisons[{index}] requires holdout_id, holdout_question, prompt, and criterion"
            )
        if holdout_id in seen:
            raise ValidationInputError(f"duplicate holdout_id in comparison design: {holdout_id}")
        seen.add(holdout_id)
        if holdout_id in contaminated:
            raise ValidationInputError(
                f"holdout record {holdout_id} is contaminated for this approach"
            )
        record = by_id.get(holdout_id)
        if record is None:
            raise ValidationInputError(f"comparison design references unknown holdout id {holdout_id}")
        matching = [
            turn for turn in record.get("turns", [])
            if turn.get("q") == question
        ]
        if len(matching) != 1 or not isinstance(matching[0].get("a"), str):
            raise ValidationInputError(
                f"holdout {holdout_id} must have exactly one answer for its declared question"
            )
        case_id = str(item.get("id", holdout_id))
        cases.append({
            "id": case_id,
            "prompt": prompt,
            "holdout_id": holdout_id,
            "context": (
                f"Declared criterion: {criterion}\n"
                "Held-out response for comparison (never expose to persona generation): "
                f"{matching[0]['a']}"
            ),
        })
    # Persona generation receives only the persona and declared probes above.
    generated = _execute_cases(
        persona=persona,
        cases=cases,
        dimension="backtest",
        persona_model=persona_model,
        persona_config=persona_config,
        judge_model=judge_model,
        judge_config=judge_config,
        telemetry_path=telemetry_path,
        persona_id=persona_id or persona["meta"].get("id"),
        persona_version=persona_version or persona["meta"].get("version"),
        study_id=study_id,
        client_id=client_id,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    generated["metadata"] = {
        "persona_id": persona_id or persona["meta"].get("id"),
        "persona_version": str(persona_version or persona["meta"].get("version") or ""),
        "persona_sha256": hashlib.sha256(Path(persona_path).read_bytes()).hexdigest(),
        "dimension": "backtest",
        "provider": persona_config.provider,
        "persona_model": persona_config.model,
        "judge_provider": judge_config.provider,
        "judge_model": judge_config.model,
        "rubric_version": RUBRIC_VERSION,
        "persona_prompt_version": PERSONA_PROMPT_VERSION,
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "probe_version": design["version"],
        "harness_version": HARNESS_VERSION,
        "generation_parameters": {
            "persona": {"temperature": temperature, "max_tokens": max_tokens},
            "judge": {
                "temperature": JUDGE_TEMPERATURE,
                "max_tokens": JUDGE_MAX_TOKENS,
            },
        },
        "comparison_design": design["version"],
        "holdout_ids_compared": [case["holdout_id"] for case in comparisons],
        "approach_hash": approach_hash,
    }
    return generated
