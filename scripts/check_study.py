#!/usr/bin/env python3
import sys,re,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/persona-lab'))
from persona_lab.core import frontmatter,load_evidence
REQ=['Hypotheses','Single-persona observations','Validate with real people','Limits']
def effective(root,pid):
 s=root/'calibration'/pid/'STATUS.md'; p=root/'personas'/f'{pid}.md'
 if not s.exists(): return 'uncalibrated'
 fm,_=frontmatter(s.read_text()); st=fm.get('status','uncalibrated')
 if st!='uncalibrated' and p.exists() and fm.get('persona_sha256')!=hashlib.sha256(p.read_bytes()).hexdigest()[:12]: return 'stale'
 return st
def check(study):
 study=study.resolve(); root=Path(__file__).resolve().parents[1]; errors=[]; warnings=[]; people=set()
 runs=sorted((study/'runs').glob('*.md')) if (study/'runs').exists() else []
 if not runs:warnings.append('no transcripts yet')
 for f in runs:
  fm,body=frontmatter(f.read_text())
  for k in ('synthetic','persona','run'):
   if not fm.get(k): errors.append(f'{f}: missing {k} frontmatter')
  if fm.get('synthetic','').lower()!='true': errors.append(f'{f}: synthetic must be true')
  if 'SYNTHETIC' not in body[:400]: errors.append(f'{f}: missing SYNTHETIC notice')
  if fm.get('persona'): people.add(fm['persona'])
 syn=study/'synthesis.md'
 if not syn.exists(): warnings.append('no synthesis yet'); return warnings,errors
 text=syn.read_text();
 for h in REQ:
  if not re.search(r'^##+\s+'+re.escape(h),text,re.I|re.M): errors.append(f'synthesis missing section: {h}')
 for block in re.findall(r'(?m)(?:^>.*(?:\n|$))+',text):
  tags=re.findall(r'\[(SYN|REAL):\s*([^\]]+)\]',block)
  if not tags: errors.append('blockquote missing provenance tag')
  for typ,val in tags:
   if typ=='SYN' and not (study/val.strip()).exists(): errors.append(f'missing SYN path: {val.strip()}')
   if typ=='REAL':
    eid=val.strip(); eid=eid if eid.startswith('E') else 'E'+eid
    try: ev=load_evidence(root/'evidence/evidence.json')
    except: ev={}
    if eid not in ev: errors.append(f'missing REAL evidence: {eid}')
    elif ev[eid].get('synthetic'): errors.append(f'REAL tag cites synthetic evidence: {eid}')
 m=re.search(r'^##+\s+Hypotheses\s*$([\s\S]*?)(?=^##+\s|\Z)',text,re.I|re.M)
 if m:
  for line in m.group(1).splitlines():
   if re.match(r'^\s*[-*+]\s+',line) and not re.search(r'\[support:\s*\d+ runs / \d+ personas\]',line,re.I): errors.append('hypothesis list item missing support tag')
 for pid in people:
  st=effective(root,pid); mm=re.search(r'^Calibration:\s*'+re.escape(pid)+r':\s*([A-Za-z-]+)',text,re.I|re.M)
  if not mm: errors.append(f'missing calibration line for {pid}')
  elif mm.group(1).lower()!=st: errors.append(f'calibration mismatch for {pid}: declared {mm.group(1)}, effective {st}')
 if not (study/'skeptic-review.md').exists(): warnings.append('no skeptic-review.md')
 if 'TODO' in text:warnings.append('leftover TODO')
 if re.search(r'participants (said|reported|told|agreed)|users (said|reported)|respondents|research (shows|found|proves|confirms)|our research|findings? (show|indicate|confirm)',text,re.I): warnings.append('language may read like real research')
 return warnings,errors
def main():
 if len(sys.argv)!=2: print('usage: check_study.py <study folder>'); return 2
 w,e=check(Path(sys.argv[1])); [print('WARNING:',x) for x in w]; [print('ERROR:',x) for x in e]; print(f'{len(e)} errors, {len(w)} warnings'); return 1 if e else 0
if __name__=='__main__': raise SystemExit(main())
