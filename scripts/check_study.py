#!/usr/bin/env python3
import sys,re,json,hashlib,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/persona-lab'))
from persona_lab.core import frontmatter,load_evidence
REQ=['Hypotheses','Single-persona observations','Validate with real people','Limits']
# v3 registry validation_status -> legacy calibration term also accepted on a synthesis "Calibration:" line
LEGACY={'not-run':'uncalibrated','invalid':'uncalibrated','fail':'failed','pass':'calibrated','warn':'calibrated','low-power':'low-power','stale':'stale'}
def effective(root,pid):
 s=root/'calibration'/pid/'STATUS.md'; p=root/'personas'/f'{pid}.md'
 if not s.exists(): return 'uncalibrated'
 fm,_=frontmatter(s.read_text()); st=fm.get('status','uncalibrated')
 if st!='uncalibrated' and p.exists() and fm.get('persona_sha256')!=hashlib.sha256(p.read_bytes()).hexdigest()[:12]: return 'stale'
 return st
def resolve_client(root,study,client):
 if client: return Path(client).resolve()
 cfg=study/'study.json'
 if cfg.exists() and json.loads(cfg.read_text()).get('client'): return root/'clients'/json.loads(cfg.read_text())['client']
 return None
def client_versions(client,study,pids,errors,warnings):
 """Resolve each persona to (version, validation_status) in a client package, enforcing exact pins and immutability."""
 regp=client/'personas/persona-registry.json'; cfg=study/'study.json'; out={}; pins={}
 reg={x['id']:x for x in json.loads(regp.read_text())['personas']} if regp.exists() else {}
 if cfg.exists():
  for p in json.loads(cfg.read_text()).get('personas',[]):
   v=str(p.get('version',''))
   if re.fullmatch(r'\d+(\.\d+)*',v): pins[p.get('id')]=v
   else: errors.append(f"study.json: persona {p.get('id')} must pin an exact version, got {v!r}")
 for pid in sorted(pids):
  e=reg.get(pid)
  if e is None: errors.append(f'persona {pid} not in {regp}'); continue
  if pid in pins: ver=pins[pid]
  elif cfg.exists(): errors.append(f'persona {pid} appears in runs but is not pinned in study.json'); continue
  else:
   cur=[x for x in e['versions'] if x.get('current')]
   if not cur: errors.append(f'persona {pid} has no current version'); continue
   ver=cur[-1]['version']; warnings.append(f'study does not pin persona versions (legacy study); resolved {pid} to current {ver}')
  v=next((x for x in e['versions'] if x['version']==ver),None)
  if v is None: errors.append(f'{pid}@{ver} not in persona registry'); continue
  f=client/v['file']
  if not f.exists(): errors.append(f'persona version file missing: {v["file"]}'); continue
  if v.get('sha256') and hashlib.sha256(f.read_bytes()).hexdigest()!=v['sha256']: errors.append(f'{pid}@{ver} changed after promotion (sha256 mismatch); promoted versions are immutable')
  out[pid]=(ver,v.get('validation_status','not-run'))
 return out
def check(study,client=None):
 study=study.resolve(); root=Path(__file__).resolve().parents[1]; errors=[]; warnings=[]; people={}
 client=resolve_client(root,study,client)
 if client is not None and not client.is_dir(): errors.append(f'client package not found: {client}'); return warnings,errors
 runs=sorted((study/'runs').glob('*.md')) if (study/'runs').exists() else []
 if not runs:warnings.append('no transcripts yet')
 for f in runs:
  fm,body=frontmatter(f.read_text())
  for k in ('synthetic','persona','run'):
   if not fm.get(k): errors.append(f'{f}: missing {k} frontmatter')
  if fm.get('synthetic','').lower()!='true': errors.append(f'{f}: synthetic must be true')
  if 'SYNTHETIC' not in body[:400]: errors.append(f'{f}: missing SYNTHETIC notice')
  if fm.get('persona'): people.setdefault(fm['persona'],{})[f.name]=fm.get('persona_version')
 versions=client_versions(client,study,set(people),errors,warnings) if client is not None else {}
 for pid,(ver,_) in versions.items():
  for name,declared in people[pid].items():
   if declared and declared!=ver: errors.append(f'runs/{name}: persona_version {declared} does not match pinned {pid}@{ver}')
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
    try: ev=load_evidence(client/'evidence' if client is not None else root/'evidence/evidence.json')
    except: ev={}
    if eid not in ev: errors.append(f'missing REAL evidence: {eid}')
    elif ev[eid].get('synthetic'): errors.append(f'REAL tag cites synthetic evidence: {eid}')
 m=re.search(r'^##+\s+Hypotheses\s*$([\s\S]*?)(?=^##+\s|\Z)',text,re.I|re.M)
 if m:
  for line in m.group(1).splitlines():
   if re.match(r'^\s*[-*+]\s+',line) and not re.search(r'\[support:\s*\d+ runs / \d+ personas\]',line,re.I): errors.append('hypothesis list item missing support tag')
 for pid in people:
  mm=re.search(r'^Calibration:\s*'+re.escape(pid)+r'(?:@([\w.-]+))?:\s*([A-Za-z-]+)',text,re.I|re.M)
  if not mm: errors.append(f'missing calibration line for {pid}'); continue
  declared=mm.group(2).lower()
  if client is None:
   st=effective(root,pid)
   if declared!=st: errors.append(f'calibration mismatch for {pid}: declared {declared}, effective {st}')
  elif pid in versions:
   ver,st=versions[pid]
   if mm.group(1) and mm.group(1)!=ver: errors.append(f'calibration line names {pid}@{mm.group(1)} but study uses {pid}@{ver}')
   if declared not in (st,LEGACY.get(st)): errors.append(f'calibration mismatch for {pid}@{ver}: declared {declared}, registry {st}')
 if not (study/'skeptic-review.md').exists(): warnings.append('no skeptic-review.md')
 if 'TODO' in text:warnings.append('leftover TODO')
 if re.search(r'participants (said|reported|told|agreed)|users (said|reported)|respondents|research (shows|found|proves|confirms)|our research|findings? (show|indicate|confirm)',text,re.I): warnings.append('language may read like real research')
 return warnings,errors
def main():
 ap=argparse.ArgumentParser(prog='check_study.py'); ap.add_argument('study'); ap.add_argument('--client',help='client package; defaults to study.json "client", else the legacy flat layout'); a=ap.parse_args()
 w,e=check(Path(a.study),a.client); [print('WARNING:',x) for x in w]; [print('ERROR:',x) for x in e]; print(f'{len(e)} errors, {len(w)} warnings'); return 1 if e else 0
if __name__=='__main__': raise SystemExit(main())
