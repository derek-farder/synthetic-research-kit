import json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/persona-lab'))
from persona_lab.core import load_evidence
def run(*args,**kw): return subprocess.run([sys.executable,*map(str,args)],capture_output=True,text=True,**kw)
def body(p): return p.read_text().split('---',2)[2]
def legacy_client(d):
 """Fictional fixtures in the legacy flat shape, with an opaque holdout file the migration must not touch."""
 for sub in ('personas','evidence','holdout','calibration/probes','calibration/dana/mock'): (d/sub).mkdir(parents=True)
 for p in ('dana','ben'): shutil.copy(ROOT/f'examples/personas/{p}.md',d/'personas')
 shutil.copy(ROOT/'examples/evidence/evidence.json',d/'evidence'); shutil.copy(ROOT/'examples/probes/dana.json',d/'calibration/probes')
 (d/'calibration/dana/mock/report.md').write_text('# mock\n'); (d/'holdout/opaque.bin').write_bytes(os.urandom(64))
 return d
class Adapters(unittest.TestCase):
 def test_every_skill_has_identical_thin_wrappers(self):
  names=sorted(p.name for p in (ROOT/'skills').iterdir())
  for base in ('.github/skills','.claude/skills'): self.assertEqual(sorted(p.name for p in (ROOT/base).iterdir()),names,base)
  for n in names:
   g=(ROOT/f'.github/skills/{n}/SKILL.md').read_text(); c=(ROOT/f'.claude/skills/{n}/SKILL.md').read_text()
   self.assertEqual(g,c,n); self.assertIn(f'/skills/{n}/SKILL.md',g); self.assertLessEqual(len(body(ROOT/f'.github/skills/{n}/SKILL.md').strip().splitlines()),1,n)
 def test_agents_match_across_platforms(self):
  for n in ('persona-runner','skeptic','insights-analyst'):
   self.assertEqual(body(ROOT/f'.github/agents/{n}.agent.md'),body(ROOT/f'.claude/agents/{n}.md'),n)
  self.assertIn("tools: ['read']",(ROOT/'.github/agents/persona-runner.agent.md').read_text())
  self.assertIn('tools: Read\n',(ROOT/'.claude/agents/persona-runner.md').read_text())
class Migration(unittest.TestCase):
 def test_moves_bytes_and_leaves_holdout_untouched(self):
  with tempfile.TemporaryDirectory() as td:
   c=legacy_client(Path(td)/'acme'); h=c/'holdout/opaque.bin'; before=(h.read_bytes(),h.stat().st_mtime_ns); dana=(c/'personas/dana.md').read_bytes()
   self.assertEqual(run(ROOT/'scripts/migrate_legacy_client.py',c).returncode,0)
   self.assertEqual((h.read_bytes(),h.stat().st_mtime_ns),before)
   self.assertEqual((c/'personas/versions/dana/1.0.md').read_bytes(),dana)
   self.assertFalse((c/'calibration').exists()); self.assertFalse((c/'personas/dana.md').exists())
   self.assertTrue((c/'validation/probes/dana.json').exists()); self.assertTrue((c/'validation/dana/legacy-unversioned/mock/report.md').exists())
   reg={x['id']:x for x in json.loads((c/'personas/persona-registry.json').read_text())['personas']}
   self.assertEqual(reg['dana']['versions'][0]['validation_status'],'not-run')
   self.assertEqual(json.loads((c/'MIGRATION.json').read_text())['migrations'][0]['holdout'],'not touched')
   self.assertIn('nothing to migrate',run(ROOT/'scripts/migrate_legacy_client.py',c).stdout)
 def test_flat_clients_dirs_move_into_named_package(self):
  with tempfile.TemporaryDirectory() as td:
   flat=legacy_client(Path(td)/'clients'); c=flat/'acme'
   self.assertEqual(run(ROOT/'scripts/migrate_legacy_client.py',c,'--from',flat).returncode,0)
   for d in ('evidence','personas','holdout','calibration'): self.assertFalse((flat/d).exists(),d)
   self.assertTrue((c/'holdout/opaque.bin').exists()); self.assertTrue((c/'evidence/evidence.json').exists())
class Checker(unittest.TestCase):
 def setUp(self):
  self.td=tempfile.TemporaryDirectory(); t=Path(self.td.name); self.client=legacy_client(t/'acme')
  run(ROOT/'scripts/migrate_legacy_client.py',self.client); self.study=t/'study'; shutil.copytree(ROOT/'examples/study',self.study)
 def tearDown(self): self.td.cleanup()
 def check(self): return run(ROOT/'scripts/check_study.py',self.study,'--client',self.client)
 def pin(self,version): (self.study/'study.json').write_text(json.dumps({'client':'acme','method':'interview','output':'research-report','personas':[{'id':'dana','version':version}],'status':'complete'}))
 def test_pinned_study_passes(self):
  self.pin('1.0'); self.assertEqual(self.check().returncode,0)
 def test_legacy_unpinned_study_passes_with_warning(self):
  p=self.check(); self.assertEqual(p.returncode,0,p.stdout); self.assertIn('does not pin persona versions',p.stdout)
 def test_floating_pin_rejected(self):
  self.pin('latest'); self.assertEqual(self.check().returncode,1)
 def test_edited_promoted_version_rejected(self):
  self.pin('1.0'); f=self.client/'personas/versions/dana/1.0.md'; f.write_text(f.read_text()+'- [E6] goal: edited after promotion.\n')
  p=self.check(); self.assertEqual(p.returncode,1); self.assertIn('changed after promotion',p.stdout)
 def test_run_version_must_match_pin(self):
  self.pin('1.0'); r=self.study/'runs/dana-r1.md'; r.write_text(r.read_text().replace('persona: dana','persona: dana\npersona_version: 2.0',1))
  self.assertEqual(self.check().returncode,1)
class Promotion(unittest.TestCase):
 def test_requires_approval_and_change_record_and_never_overwrites(self):
  with tempfile.TemporaryDirectory() as td:
   t=Path(td); c=t/'acme'; shutil.copytree(ROOT/'clients/_template',c); draft=t/'dana.md'; shutil.copy(ROOT/'examples/personas/dana.md',draft)
   prop={'persona_id':'dana','to_version':'1.0','proposed_persona_file':str(draft),'approval':'pending','reasoning':{'claims_added':['all']},'evidence_delta':{'evidence_added':['E1']}}
   def promote(**kw):
    pp=t/'p.json'; pp.write_text(json.dumps({**prop,**kw})); return run(ROOT/'scripts/promote_persona_version.py',c,pp)
   self.assertNotEqual(promote().returncode,0)
   self.assertNotEqual(promote(approval='approved',reasoning={}).returncode,0)
   self.assertEqual(promote(approval='approved').returncode,0)
   v=c/'personas/versions/dana/1.0.md'; first=v.read_bytes(); draft.write_text('changed')
   self.assertNotEqual(promote(approval='approved').returncode,0); self.assertEqual(v.read_bytes(),first)
class Ingestion(unittest.TestCase):
 def test_raw_is_unchanged_and_edits_are_refused(self):
  with tempfile.TemporaryDirectory() as td:
   c=Path(td)/'acme'; shutil.copytree(ROOT/'clients/_template',c); raw=c/'sources/raw/example.csv'
   shutil.copy(ROOT/'examples/client-fictional-medtech/sources/raw/example.csv',raw); before=raw.read_bytes()
   self.assertEqual(run(ROOT/'scripts/ingest_sources.py',c).returncode,0); self.assertEqual(raw.read_bytes(),before)
   rows=[json.loads(x) for x in (c/'evidence/evidence.jsonl').read_text().splitlines() if x]
   self.assertEqual(len(rows),3); self.assertTrue(all(r['synthetic'] is False for r in rows))
   self.assertEqual(json.loads(run(ROOT/'scripts/ingest_sources.py',c).stdout)['sources_added'],0)
   raw.write_bytes(before+b'R4,Segment B,Wave 3,setup,"edited"\n'); batches=(c/'evidence/ingestion-batches.json').read_text()
   self.assertNotEqual(run(ROOT/'scripts/ingest_sources.py',c).returncode,0); self.assertEqual((c/'evidence/ingestion-batches.json').read_text(),batches)
   self.assertEqual(len(load_evidence(c/'evidence')),3)
class Evidence(unittest.TestCase):
 def test_directory_merge_rejects_duplicate_ids(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td); shutil.copy(ROOT/'examples/evidence/evidence.json',d)
   (d/'evidence.jsonl').write_text(json.dumps({'id':'E1','source_id':'S','evidence_type':'text','text':'x','synthetic':False})+'\n')
   with self.assertRaises(ValueError): load_evidence(d)
class Hook(unittest.TestCase):
 def test_pre_commit_blocks_client_and_legacy_data(self):
  with tempfile.TemporaryDirectory() as td:
   t=Path(td); subprocess.run(['git','init','-q',str(t)],check=True)
   def staged(path):
    (t/path).parent.mkdir(parents=True,exist_ok=True); (t/path).write_text('x'); subprocess.run(['git','-C',str(t),'add','-f',path],check=True)
    rc=subprocess.run([sys.executable,str(ROOT/'.githooks/pre-commit')],cwd=t,capture_output=True).returncode
    subprocess.run(['git','-C',str(t),'rm','-q','--cached',path],check=True); return rc
   for p in ('clients/acme/evidence/evidence.json','clients/acme/holdout/h.json','studies/s/synthesis.md','holdout/h.json','personas/p.md'): self.assertEqual(staged(p),1,p)
   for p in ('clients/_template/CLIENT.md','studies/_template/study.json','skills/x/SKILL.md'): self.assertEqual(staged(p),0,p)
if __name__=='__main__':unittest.main()
