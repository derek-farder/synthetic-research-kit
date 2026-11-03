import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LeakageCommandTests(unittest.TestCase):
    def run_leakage(self, holdout_record):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            holdout = root / "holdout.json"
            holdout.write_text(json.dumps([holdout_record]))
            out = root / "validation"
            persona = ROOT / "examples/personas/dana.md"
            evidence = ROOT / "examples/evidence/evidence.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/persona-lab"),
                    "leakage",
                    "--persona",
                    str(persona),
                    "--evidence",
                    str(evidence),
                    "--holdout",
                    str(holdout),
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )
            data = json.loads((out / "results.json").read_text())
            report = (out / "report.md").read_text()
            return result, data, report, persona

    def test_leakage_command_records_deterministic_result_without_mock_scores(self):
        result, data, report, persona = self.run_leakage(
            {
                "id": "held-out-interview",
                "persona_id": "dana",
                "turns": [{"q": "unrelated", "a": "No shared wording in this answer."}],
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data["dimensions"]["leakage"], "PASS")
        self.assertEqual(data["dimensions"]["backtest"], "NOT-RUN")
        self.assertEqual(data["dimensions"]["coherence"], "NOT-RUN")
        self.assertEqual(data["dimensions"]["abstention"], "NOT-RUN")
        self.assertEqual(data["dimensions"]["framing_resistance"], "NOT-RUN")
        self.assertEqual(data["dimensions"]["distinctiveness"], "NOT-RUN")
        self.assertEqual(data["meta"]["persona_sha256"], hashlib.sha256(persona.read_bytes()).hexdigest())
        self.assertFalse(data["meta"]["mock"])
        self.assertTrue(data["meta"]["deterministic"])
        self.assertIn("not a persona behavioral validation", report)
        self.assertNotIn("backtest.stance", data)

    def test_leakage_command_returns_invalid_when_overlap_is_found(self):
        result, data, report, _ = self.run_leakage(
            {
                "id": "held-out-interview",
                "persona_id": "dana",
                "turns": [
                    {
                        "q": "test",
                        "a": "I skip extra device screens when the patient needs me at the bedside.",
                    }
                ],
            }
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(data["dimensions"]["leakage"], "INVALID")
        self.assertGreater(data["leakage"]["leak_count"], 0)
        self.assertIn("Leakage: INVALID", report)
        self.assertNotIn("The pump alarms clearly", report)


if __name__ == "__main__":
    unittest.main()
