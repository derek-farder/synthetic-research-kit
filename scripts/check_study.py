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
 cfg_path=study/'study.json'
 if cfg_path.exists():
  try:
   cfg_data=json.loads(cfg_path.read_text())
  except (OSError,json.JSONDecodeError) as exc:
   errors.append(f'study.json is invalid: {exc}'); cfg_data={}
  snapshot=cfg_data.get('execution_snapshot')
  if cfg_data.get('study_format_version')=='3.1' and cfg_data.get('status') in ('running','complete') and snapshot is None:
   errors.append('v3.1 executed study is missing its execution_snapshot')
  if snapshot is not None:
   if not isinstance(snapshot,dict): errors.append('execution_snapshot must be an object')
   elif client is not None:
    reg_path=client/'personas/persona-registry.json'
    try: reg={item['id']:item for item in json.loads(reg_path.read_text())['personas']}
    except (OSError,KeyError,json.JSONDecodeError,TypeError): reg={}
    snapshot_personas=snapshot.get('personas',[])
    if not isinstance(snapshot_personas,list) or not snapshot_personas: errors.append('execution_snapshot must pin personas')
    config_pins={(item.get('id'),str(item.get('version'))) for item in cfg_data.get('personas',[]) if isinstance(item,dict)}
    snapshot_pins={(item.get('id'),str(item.get('version'))) for item in snapshot_personas if isinstance(item,dict)} if isinstance(snapshot_personas,list) else set()
    if config_pins!=snapshot_pins: errors.append('execution_snapshot persona pins do not match study.json')
    for pinned in snapshot_personas if isinstance(snapshot_personas,list) else []:
     pid=pinned.get('id'); ver=str(pinned.get('version','')); entry=reg.get(pid)
     registered=next((v for v in entry.get('versions',[]) if str(v.get('version'))==ver),None) if entry else None
     if not registered: errors.append(f'execution_snapshot persona {pid}@{ver} is not registered')
     else:
      persona_file=client/registered['file']
      if not persona_file.exists(): errors.append(f'execution_snapshot persona file missing: {registered["file"]}')
      elif hashlib.sha256(persona_file.read_bytes()).hexdigest()!=pinned.get('sha256'): errors.append(f'execution_snapshot persona hash mismatch for {pid}@{ver}')
     profile=pinned.get('validation_profile')
     if not isinstance(profile,dict) or not isinstance(profile.get('aggregate_status'),str) or not isinstance(profile.get('dimensions'),dict):
      errors.append(f'execution_snapshot validation profile missing or malformed for {pid}@{ver}')
   for field in ('method','output_contract','execution'):
    if not isinstance(snapshot.get(field),dict): errors.append(f'execution_snapshot.{field} is required')
   if not isinstance(snapshot.get('limitations'),list) or not snapshot.get('limitations'): errors.append('execution_snapshot limitations are required')
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
    elif not ev[eid].get('grounding_eligible',False):
     errors.append(f"REAL tag cites ineligible evidence {eid}: {ev[eid].get('eligibility_reason','unknown eligibility')}")
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
