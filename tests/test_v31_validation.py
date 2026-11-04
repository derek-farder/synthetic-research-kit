import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/persona-lab"))

from persona_lab.models import ModelConfig, ModelResponse
from persona_lab.cli import _update_live_profile
from persona_lab.validation import (
    ValidationInputError,
    mark_holdout_contaminated,
    run_backtest,
    run_behavioral_dimension,
)


class SequenceModel:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.messages = []

    def complete(self, messages, *, temperature=0.0, max_tokens=1024):
        self.messages.append(messages)
        return next(self.responses)

    def complete_with_usage(self, messages, *, temperature=0.0, max_tokens=1024):
        self.messages.append(messages)
        return ModelResponse(next(self.responses), input_tokens=23, output_tokens=7)


def model_config(role="persona"):
    return ModelConfig(
        role=role,
        provider="test-provider",
        model=f"test-{role}-deployment",
        endpoint="https://test.invalid",
        api_version="test",
        auth_method="api-key",
        credential_env="TEST_KEY",
        credential="not-serialized",
    )


class BehavioralValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.persona_path = ROOT / "examples/personas/dana.md"
        self.telemetry = self.root / "telemetry.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def write_design(self, data):
        path = self.root / "design.json"
        path.write_text(json.dumps(data))
        return path

    def test_judge_drives_dimension_result_and_metadata_captures_both_models(self):
        probes = self.write_design(
            {
                "version": "coherence-probes-v1",
                "probes": [{"id": "p1", "prompt": "Describe a routine choice."}],
            }
        )
        persona_model = SequenceModel(["generated answer"])
        judge_model = SequenceModel(
            ['{"verdict":"PASS","rationale":"Consistent with the persona boundaries."}']
        )

        result = run_behavioral_dimension(
            dimension="coherence",
            persona_path=self.persona_path,
            probe_path=probes,
            persona_model=persona_model,
            persona_config=model_config(),
            judge_model=judge_model,
            judge_config=model_config("judge"),
            telemetry_path=self.telemetry,
            study_id="study-1",
            client_id="client-1",
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["metadata"]["persona_sha256"], hashlib.sha256(self.persona_path.read_bytes()).hexdigest())
        self.assertEqual(result["metadata"]["provider"], "test-provider")
        self.assertEqual(result["metadata"]["persona_model"], "test-persona-deployment")
        self.assertEqual(result["metadata"]["judge_model"], "test-judge-deployment")
        self.assertEqual(
            result["metadata"]["persona_prompt_version"],
            "persona-generation-v1",
        )
        self.assertEqual(
            result["metadata"]["judge_prompt_version"],
            "independent-judge-v1",
        )
        self.assertEqual(result["metadata"]["generation_parameters"]["judge"], {
            "temperature": 0.0,
            "max_tokens": 512,
        })
        calls = [json.loads(line) for line in self.telemetry.read_text().splitlines()]
        self.assertEqual([call["operation_type"] for call in calls], [
            "persona_generation:coherence",
            "rubric_evaluation:coherence",
        ])
        self.assertEqual(calls[0]["input_tokens"], 23)
        self.assertEqual(calls[0]["output_tokens"], 7)
        self.assertEqual(calls[0]["study_id"], "study-1")
        self.assertEqual(calls[0]["client_id"], "client-1")
        self.assertNotIn("not-serialized", self.telemetry.read_text())
        self.assertNotIn("generated answer", self.telemetry.read_text())

    def test_live_dimension_profile_records_models_without_changing_aggregate_status(self):
        client_root = self.root / "clients/c1"
        version_file = client_root / "personas/versions/dana/1.0.md"
        version_file.parent.mkdir(parents=True)
        shutil.copyfile(self.persona_path, version_file)
        registry_path = client_root / "personas/persona-registry.json"
        registry_path.write_text(json.dumps({
            "personas": [{
                "id": "dana",
                "versions": [{
                    "version": "1.0",
                    "file": "personas/versions/dana/1.0.md",
                    "sha256": hashlib.sha256(version_file.read_bytes()).hexdigest(),
                    "validation_status": "not-run",
                }],
            }]
        }))
        result = {
            "status": "PASS",
            "metadata": {
                "persona_id": "dana",
                "persona_version": "1.0",
                "persona_sha256": hashlib.sha256(version_file.read_bytes()).hexdigest(),
                "provider": "persona-provider",
                "persona_model": "persona-deployment",
                "judge_provider": "judge-provider",
                "judge_model": "judge-deployment",
                "persona_prompt_version": "persona-generation-v1",
                "judge_prompt_version": "independent-judge-v1",
                "rubric_version": "behavioral-rubrics-v1",
                "probe_version": "coherence-probes-v1",
                "harness_version": "3.1.0",
                "generation_parameters": {
                    "persona": {"temperature": 0.2, "max_tokens": 900},
                    "judge": {"temperature": 0.0, "max_tokens": 512},
                },
            },
        }

        _update_live_profile(
            version_file,
            dimension="coherence",
            result=result,
            result_path=self.root / "results.json",
        )

        version = json.loads(registry_path.read_text())["personas"][0]["versions"][0]
        self.assertEqual(version["validation_status"], "not-run")
        self.assertEqual(
            version["validation_dimensions"]["coherence"]["judge_model"],
            "judge-deployment",
        )
        self.assertEqual(
            version["validation_dimensions"]["coherence"]["generation_parameters"],
            result["metadata"]["generation_parameters"],
        )

    def test_framing_judge_receives_all_framed_outputs_together(self):
        probes = self.write_design(
            {
                "version": "framing-probes-v1",
                "scenarios": [
                    {"id": "s1", "framings": ["Neutral wording A", "Neutral wording B"]}
                ],
            }
        )
        persona_model = SequenceModel(["response A", "response B"])
        judge_model = SequenceModel(
            ['{"verdict":"WARN","rationale":"The responses differ in one priority."}']
        )
        result = run_behavioral_dimension(
            dimension="framing_resistance",
            persona_path=self.persona_path,
            probe_path=probes,
            persona_model=persona_model,
            persona_config=model_config(),
            judge_model=judge_model,
            judge_config=model_config("judge"),
            telemetry_path=self.telemetry,
        )
        self.assertEqual(result["status"], "WARN")
        judge_payload = judge_model.messages[0][1]["content"]
        self.assertIn("response A", judge_payload)
        self.assertIn("response B", judge_payload)

    def test_abstention_requires_answerable_and_out_of_scope_probes(self):
        probes = self.write_design(
            {
                "version": "abstention-probes-v1",
                "probes": [
                    {"id": "in", "scope": "answerable", "prompt": "A grounded question"},
                    {"id": "out", "scope": "out_of_scope", "prompt": "An unknown statistic"},
                ],
            }
        )
        result = run_behavioral_dimension(
            dimension="abstention",
            persona_path=self.persona_path,
            probe_path=probes,
            persona_model=SequenceModel(["in scope answer", "I do not know"]),
            persona_config=model_config(),
            judge_model=SequenceModel([
                '{"verdict":"PASS","rationale":"Answers within stated scope."}',
                '{"verdict":"PASS","rationale":"Appropriately abstains."}',
            ]),
            judge_config=model_config("judge"),
            telemetry_path=self.telemetry,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["cases"]), 2)

    def test_distinctiveness_generates_target_and_comparison_personas(self):
        other = self.root / "other.md"
        other.write_text(
            "---\nid: other\nversion: 1.0\n---\n# Other persona\n"
            "## Profile\nA different fictional profile.\n"
            "## Claims\n- [E1] behavior: Uses a different stated approach.\n"
        )
        probes = self.write_design({
            "version": "distinctiveness-probes-v1",
            "probes": [{"id": "p1", "prompt": "What would you consider?"}],
        })
        persona_model = SequenceModel(["target response", "comparison response"])
        judge_model = SequenceModel([
            '{"verdict":"PASS","rationale":"Responses express distinct priorities."}'
        ])
        result = run_behavioral_dimension(
            dimension="distinctiveness",
            persona_path=self.persona_path,
            probe_path=probes,
            persona_model=persona_model,
            persona_config=model_config(),
            judge_model=judge_model,
            judge_config=model_config("judge"),
            telemetry_path=self.telemetry,
            other_persona_paths=[other],
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(persona_model.messages), 2)
        self.assertIn("comparison response", judge_model.messages[0][1]["content"])
        self.assertEqual(result["metadata"]["comparison_personas"][0]["id"], "other")
        self.assertEqual(
            result["metadata"]["comparison_personas"][0]["sha256"],
            hashlib.sha256(other.read_bytes()).hexdigest(),
        )

    def test_mock_validation_cannot_pass_or_update_registry(self):
        probes = self.write_design(
            {
                "version": "coherence-probes-v1",
                "probes": [{"id": "p1", "prompt": "Prompt"}],
            }
        )
        client_root = self.root / "clients/c1"
        version_file = client_root / "personas/versions/dana/1.0.md"
        version_file.parent.mkdir(parents=True)
        shutil.copyfile(self.persona_path, version_file)
        (client_root / "client.json").write_text(json.dumps({"client_id": "c1"}))
        registry_path = client_root / "personas/persona-registry.json"
        registry_path.write_text(json.dumps({
            "personas": [{
                "id": "dana",
                "versions": [{
                    "version": "1.0",
                    "file": "personas/versions/dana/1.0.md",
                    "sha256": hashlib.sha256(version_file.read_bytes()).hexdigest(),
                    "validation_status": "not-run",
                }],
            }]
        }))
        before = registry_path.read_text()
        out = self.root / "mock-output"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/persona-lab"),
                "coherence",
                "--persona", str(version_file),
                "--evidence", str(ROOT / "examples/evidence/evidence.json"),
                "--probes", str(probes),
                "--out", str(out),
                "--mock",
            ],
            capture_output=True,
            text=True,
        )
        report = json.loads((out / "results.json").read_text())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "MOCK")
        self.assertNotEqual(report["status"], "PASS")
        self.assertNotIn("verdict", report["cases"][0])
        self.assertEqual(registry_path.read_text(), before)

    def test_backtest_generation_never_receives_holdout_answer(self):
        holdout_dir = self.root / "clients/c1/holdout"
        holdout_dir.mkdir(parents=True)
        (holdout_dir / "records.json").write_text(json.dumps([
            {
                "id": "h-1",
                "persona_id": "dana",
                "turns": [{"q": "What happened?", "a": "PRIVATE HELDOUT ANSWER"}],
            }
        ]))
        design = self.write_design({
            "version": "backtest-comparison-v1",
            "comparisons": [{
                "holdout_id": "h-1",
                "holdout_question": "What happened?",
                "prompt": "Describe a disruption.",
                "criterion": "Compare the stated response strategy.",
            }],
        })
        persona_model = SequenceModel(["generated strategy"])
        judge_model = SequenceModel([
            '{"verdict":"PASS","rationale":"The declared strategy is aligned."}'
        ])
        result = run_backtest(
            persona_path=self.persona_path,
            holdout_path=holdout_dir,
            comparison_design_path=design,
            persona_model=persona_model,
            persona_config=model_config(),
            judge_model=judge_model,
            judge_config=model_config("judge"),
            telemetry_path=self.telemetry,
            contamination_ledger_path=self.root / "contamination.json",
            approach_hash="approach-v1",
        )
        generation_payload = json.dumps(persona_model.messages)
        self.assertNotIn("PRIVATE HELDOUT ANSWER", generation_payload)
        self.assertIn("PRIVATE HELDOUT ANSWER", judge_model.messages[0][1]["content"])
        self.assertEqual(result["cases"][0]["holdout_id"], "h-1")

    def test_backtest_requires_controlled_holdout_path_and_design(self):
        with self.assertRaises(ValidationInputError):
            run_backtest(
                persona_path=self.persona_path,
                holdout_path=self.root / "ordinary.json",
                comparison_design_path=self.write_design({
                    "version": "backtest-comparison-v1",
                    "comparisons": [],
                }),
                persona_model=SequenceModel([]),
                persona_config=model_config(),
                judge_model=SequenceModel([]),
                judge_config=model_config("judge"),
                telemetry_path=self.telemetry,
                contamination_ledger_path=self.root / "contamination.json",
                approach_hash="v1",
            )

    def test_contamination_ledger_blocks_same_approach(self):
        ledger = self.root / "contamination.json"
        mark_holdout_contaminated(
            ledger_path=ledger,
            holdout_id="h-1",
            revised_approach_hash="approach-v2",
            reason="Holdout-informed persona revision.",
        )
        self.assertEqual(json.loads(ledger.read_text())["events"][0]["holdout_id"], "h-1")
        holdout_dir = self.root / "clients/c1/holdout"
        holdout_dir.mkdir(parents=True)
        (holdout_dir / "records.json").write_text(json.dumps([
            {
                "id": "h-1",
                "persona_id": "dana",
                "turns": [{"q": "What happened?", "a": "A holdout response."}],
            }
        ]))
        design = self.write_design({
            "version": "backtest-comparison-v1",
            "comparisons": [{
                "holdout_id": "h-1",
                "holdout_question": "What happened?",
                "prompt": "Describe a disruption.",
                "criterion": "Compare the stated response strategy.",
            }],
        })
        with self.assertRaisesRegex(ValidationInputError, "contaminated"):
            run_backtest(
                persona_path=self.persona_path,
                holdout_path=holdout_dir,
                comparison_design_path=design,
                persona_model=SequenceModel([]),
                persona_config=model_config(),
                judge_model=SequenceModel([]),
                judge_config=model_config("judge"),
                telemetry_path=self.telemetry,
                contamination_ledger_path=ledger,
                approach_hash="approach-v2",
            )

    def test_contamination_requires_reason_and_hash(self):
        with self.assertRaises(ValidationInputError):
            mark_holdout_contaminated(
                ledger_path=self.root / "ledger.json",
                holdout_id="h1",
                revised_approach_hash="",
                reason="",
            )


if __name__ == "__main__":
    unittest.main()
