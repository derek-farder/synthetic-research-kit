#!/usr/bin/env python3
import argparse,json,shutil,hashlib,datetime,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('client_dir');ap.add_argument('proposal_json');a=ap.parse_args();c=Path(a.client_dir);p=json.loads(Path(a.proposal_json).read_text())
if p.get('approval')!='approved':raise SystemExit('proposal must be explicitly approved')
missing=[k for k in ('persona_id','to_version','proposed_persona_file','reasoning','evidence_delta') if not p.get(k)]
if missing:raise SystemExit('proposal missing change record: '+', '.join(missing))
if not re.fullmatch(r'\d+(\.\d+)*',str(p['to_version'])):raise SystemExit('to_version must be an exact version like 1.1')
pid,ver=p['persona_id'],p['to_version'];src=Path(p['proposed_persona_file']);
if not src.is_file():raise SystemExit(f'proposed persona file not found: {src}')
dst=c/'personas/versions'/pid/f'{ver}.md';dst.parent.mkdir(parents=True,exist_ok=True)
if dst.exists():raise SystemExit('immutable version exists')
shutil.copy2(src,dst);rp=c/'personas/persona-registry.json';r=json.loads(rp.read_text());e=next((x for x in r['personas'] if x['id']==pid),None)
if e is None:e={'id':pid,'versions':[]};r['personas'].append(e)
for x in e['versions']:x['current']=False
e['versions'].append({'version':ver,'file':str(dst.relative_to(c)),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'current':True,'validation_status':'not-run','promoted_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reasoning':p.get('reasoning',{}),'evidence_delta':p.get('evidence_delta',{})});rp.write_text(json.dumps(r,indent=2));print(dst)
