import json,subprocess,tempfile,shutil,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Tests(unittest.TestCase):
 def test_lint(self):
  with tempfile.TemporaryDirectory() as td:
   p=subprocess.run([str(ROOT/'scripts/persona-lab'),'lint','--persona',str(ROOT/'examples/personas/dana.md'),'--evidence',str(ROOT/'examples/evidence/evidence.json'),'--out',td])
   self.assertEqual(p.returncode,1)
   r=json.loads((Path(td)/'results.json').read_text()); self.assertEqual(r['tests']['lint.errors'],0); self.assertEqual(r['tests']['lint.grounded'],1)
 def test_checker(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   d=Path(td)/'study'; shutil.copytree(ROOT/'examples/study',d)
   live=ROOT/'evidence/evidence.json'; live.parent.mkdir(exist_ok=True); prior=live.read_bytes() if live.exists() else None; shutil.copy(ROOT/'examples/evidence/evidence.json',live)
   try:self.assertEqual(subprocess.run([sys.executable,str(ROOT/'scripts/check_study.py'),str(d)]).returncode,0)
   finally:
    if prior is None: live.unlink()
    else: live.write_bytes(prior)
if __name__=='__main__':unittest.main()
