import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research_os.application import (
    ClientService,
    EvidenceService,
    FilesystemRepository,
    InsightService,
    PersonaService,
    ReportService,
    StudyService,
    ValidationService,
)


class ApplicationServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = FilesystemRepository(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, path, value):
        self.repo.write_text(path, json.dumps(value))

    def test_domain_services_wrap_filesystem_package_layout(self):
        persona_text = "---\nid: p1\nversion: 1.0\n---\nPersona"
        self.repo.write_text("clients/c1/client.json", json.dumps({"client_id": "c1"}))
        self.repo.write_text("clients/_template/client.json", json.dumps({"client_id": "TEMPLATE"}))
        self.repo.write_text(
            "clients/c1/evidence/evidence.jsonl",
            json.dumps({"id": "E1", "text": "source"}) + "\n",
        )
        self.write_json("clients/c1/personas/persona-registry.json", {"personas": []})
        self.repo.write_text("clients/c1/personas/versions/p1/1.0.md", persona_text)
        self.write_json("clients/c1/insights/insight-registry.json", {"insights": []})
        self.write_json(
            "clients/c1/validation/p1/1.0/run-1/results.json",
            {"status": "WARN"},
        )
        self.repo.write_text("studies/s1/research-report.md", "Report")

        self.assertEqual(ClientService(self.repo).get("c1")["client_id"], "c1")
        self.assertEqual([x["client_id"] for x in ClientService(self.repo).list()], ["c1"])
        self.assertEqual(EvidenceService(self.repo).records("c1")[0]["id"], "E1")
        self.assertEqual(PersonaService(self.repo).version("c1", "p1", "1.0"), persona_text)
        self.assertEqual(InsightService(self.repo).registry("c1")["insights"], [])
        self.assertEqual(
            ValidationService(self.repo).result("c1", "p1", "1.0", "run-1")["status"],
            "WARN",
        )
        reports = ReportService(self.repo)
        self.assertEqual(reports.read("s1"), "Report")
        reports.write("s1", "Updated")
        self.assertEqual(reports.read("s1"), "Updated")

    def test_filesystem_repository_rejects_path_escape(self):
        with self.assertRaises(ValueError):
            self.repo.read_text("../outside")

    def create_approved_study(self):
        persona_text = "---\nid: p1\nversion: 1.0\n---\nPersona content".replace(
            "\n", "\r\n"
        )
        persona_path = self.root / "clients/c1/personas/versions/p1/1.0.md"
        persona_path.parent.mkdir(parents=True)
        persona_path.write_bytes(persona_text.encode("utf-8"))
        digest = hashlib.sha256(persona_path.read_bytes()).hexdigest()
        self.write_json(
            "clients/c1/personas/persona-registry.json",
            {
                "personas": [{
                    "id": "p1",
                    "versions": [{
                        "version": "1.0",
                        "file": "personas/versions/p1/1.0.md",
                        "sha256": digest,
                        "validation_status": "not-run",
                        "validation_dimensions": {
                            "coherence": {"status": "WARN", "persona_model": "model-a"}
                        },
                    }],
                }]
            },
        )
        self.write_json(
            "studies/s1/study.json",
            {
                "client": "c1",
                "method": "interview",
                "output": "research-report",
                "personas": [{"id": "p1", "version": "1.0"}],
                "runs_per_persona": 3,
                "status": "approved",
            },
        )

    def test_execution_snapshot_is_immutable_and_captures_profiles(self):
        self.create_approved_study()
        studies = StudyService(self.repo)
        snapshot = studies.snapshot_execution(
            study_id="s1",
            client_id="c1",
            execution_provider="azure-openai",
            execution_model="approved-deployment",
            limitations=["Fictional test only."],
            method_version="1.0",
            output_contract_version="1.0",
        )
        self.assertEqual(snapshot["personas"][0]["sha256"], hashlib.sha256(
            (self.root / "clients/c1/personas/versions/p1/1.0.md").read_bytes()
        ).hexdigest())
        self.assertEqual(
            snapshot["personas"][0]["validation_profile"]["dimensions"]["coherence"]["status"],
            "WARN",
        )
        self.assertEqual(snapshot["execution"]["model"], "approved-deployment")
        self.assertEqual(
            studies.configuration("s1")["study_format_version"],
            "3.1",
        )
        self.assertEqual(studies.configuration("s1")["status"], "running")
        config_before = studies.configuration("s1")

        registry_path = "clients/c1/personas/persona-registry.json"
        registry = json.loads(self.repo.read_text(registry_path))
        registry["personas"][0]["versions"][0]["validation_dimensions"]["coherence"]["status"] = "PASS"
        self.write_json(registry_path, registry)
        self.assertEqual(
            studies.configuration("s1")["execution_snapshot"],
            config_before["execution_snapshot"],
        )
        with self.assertRaisesRegex(ValueError, "immutable"):
            studies.snapshot_execution(
                study_id="s1",
                client_id="c1",
                execution_provider="azure-openai",
                execution_model="another-model",
                limitations=["Changed."],
                method_version="1.0",
                output_contract_version="1.0",
            )

    def test_snapshot_requires_approved_study_and_limitations(self):
        self.create_approved_study()
        config = json.loads(self.repo.read_text("studies/s1/study.json"))
        config["status"] = "draft"
        self.write_json("studies/s1/study.json", config)
        with self.assertRaisesRegex(ValueError, "approved"):
            StudyService(self.repo).snapshot_execution(
                study_id="s1",
                client_id="c1",
                execution_provider="azure",
                execution_model="m",
                limitations=["limit"],
                method_version="1.0",
                output_contract_version="1.0",
            )

    def test_v31_executed_studies_require_snapshots_but_legacy_v3_remains_compatible(self):
        study = self.root / "legacy"
        study.mkdir()
        config_path = study / "study.json"
        config_path.write_text(json.dumps({
            "method": "interview",
            "output": "research-report",
            "personas": [],
            "status": "complete",
        }))
        checker = ROOT / "scripts/check_study.py"
        legacy = subprocess.run(
            [sys.executable, str(checker), str(study)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(legacy.returncode, 0, legacy.stdout + legacy.stderr)

        config = json.loads(config_path.read_text())
        config["study_format_version"] = "3.1"
        config_path.write_text(json.dumps(config))
        current = subprocess.run(
            [sys.executable, str(checker), str(study)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(current.returncode, 1)
        self.assertIn("missing its execution_snapshot", current.stdout)


if __name__ == "__main__":
    unittest.main()
