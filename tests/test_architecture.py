import unittest,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
 def test_core(self):
  for p in ['ARCHITECTURE.md','schemas/evidence-record.schema.json','skills/analyze-insights/SKILL.md','.github/agents/insights-analyst.agent.md','.claude/agents/insights-analyst.md','outputs/research-report/OUTPUT.md','scripts/ingest_sources.py','scripts/promote_persona_version.py']:
   self.assertTrue((R/p).exists(),p)
 def test_schemas(self):
  for p in (R/'schemas').glob('*.json'):json.loads(p.read_text())
  evidence=json.loads((R/'schemas/evidence-record.schema.json').read_text())
  self.assertIn('provenance_type',evidence['required']);self.assertIn('fixture',evidence['required'])
  self.assertEqual(evidence['properties']['provenance_type']['enum'],['source','derived','analytical','simulation'])
  self.assertEqual(evidence['properties']['fixture']['type'],'boolean')
 def test_no_blueprints(self):
  self.assertFalse((R/'outputs/service-blueprint').exists());self.assertFalse((R/'outputs/journey-map').exists())
 def test_thin_adapters(self):
  g=(R/'.github/skills/analyze-insights/SKILL.md').read_text();c=(R/'.claude/skills/analyze-insights/SKILL.md').read_text();self.assertEqual(g,c);self.assertIn('/skills/analyze-insights/SKILL.md',g)
if __name__=='__main__':unittest.main()
