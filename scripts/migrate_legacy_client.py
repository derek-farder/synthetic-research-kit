#!/usr/bin/env python3
"""Move a legacy flat client layout into the v3 client package layout.

legacy                          -> v3 client package
personas/<id>.md                -> personas/versions/<id>/1.0.md (+ persona-registry.json entry)
calibration/probes/<id>.json    -> validation/probes/<id>.json
calibration/<id>/**             -> validation/<id>/legacy-unversioned/**
evidence/*                      -> evidence/* (unchanged)
holdout/*                       -> holdout/* (moved without opening; untouched when migrating in place)

Files move byte-for-byte and are verified by sha256. MIGRATION.json records every move.
Use --from when the legacy folders sit outside the package (e.g. flat clients/evidence, clients/personas).
"""
import argparse,datetime,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/persona-lab'))
from persona_lab.core import frontmatter
LEGACY_STATUS={'calibrated':'pass','low-power':'low-power','failed':'fail','stale':'stale','uncalibrated':'not-run'}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def plan(old,c):
 """Return [(src,dst)] for every hashed file move, plus holdout entries moved unopened."""
 moves=[]; holdout=[]
 for f in sorted((old/'personas').glob('*.md')) if (old/'personas').is_dir() else []:
  if f.name!='PERSONA-TEMPLATE.md': moves.append((f,c/'personas/versions'/f.stem/'1.0.md'))
 cal=old/'calibration'
 if cal.is_dir():
  for f in sorted(x for x in cal.rglob('*') if x.is_file() and x.name not in ('.gitkeep','.DS_Store')):
   rel=f.relative_to(cal)
   if rel.parts[0]=='probes': dst=c/'validation/probes'/Path(*rel.parts[1:])
   elif len(rel.parts)>1: dst=c/'validation'/rel.parts[0]/'legacy-unversioned'/Path(*rel.parts[1:])
   else: dst=c/'validation/legacy-calibration'/rel
   moves.append((f,dst))
 if old!=c:
  for f in sorted(x for x in (old/'evidence').iterdir() if x.is_file()) if (old/'evidence').is_dir() else []:
   if f.name!='.gitkeep': moves.append((f,c/'evidence'/f.name))
  if (old/'holdout').is_dir(): holdout=[(x,c/'holdout'/x.name) for x in sorted((old/'holdout').iterdir()) if x.name!='.gitkeep']
 return moves,holdout
def status_for(old,pid,persona):
 s=old/'calibration'/pid/'STATUS.md'
 if not s.exists(): return 'not-run'
 fm,_=frontmatter(s.read_text()); st=LEGACY_STATUS.get(fm.get('status','uncalibrated'),'not-run')
 if st!='not-run' and fm.get('persona_sha256') and fm['persona_sha256']!=sha(persona)[:12]: return 'stale'
 return st
def main():
 ap=argparse.ArgumentParser(prog='migrate_legacy_client.py'); ap.add_argument('client_dir'); ap.add_argument('--from',dest='legacy'); ap.add_argument('--dry-run',action='store_true'); a=ap.parse_args()
 c=Path(a.client_dir).resolve(); old=Path(a.legacy).resolve() if a.legacy else c
 moves,holdout=plan(old,c)
 if not moves and not holdout: print('nothing to migrate'); return 0
 clash=[str(d) for _,d in moves+holdout if d.exists()]
 if clash: print('ERROR: refusing to overwrite:',*clash,sep='\n  '); return 1
 for s,d in moves: print(f'{s.relative_to(old)} -> {d.relative_to(c)}')
 for s,d in holdout: print(f'{s.relative_to(old)} -> {d.relative_to(c)} (holdout: moved unopened)')
 if a.dry_run: return 0
 statuses={s.stem:status_for(old,s.stem,s) for s,d in moves if d.parent.parent.name=='versions'}
 # Fill in missing package structure from the template; never overwrite and never add to an existing holdout folder.
 targets={d for _,d in moves+holdout}
 for t in sorted((ROOT/'clients/_template').rglob('*')):
  rel=t.relative_to(ROOT/'clients/_template'); d=c/rel
  if t.is_file() and not d.exists() and d not in targets and not (rel.parts[0]=='holdout' and (old/'holdout').is_dir()):
   d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(t,d)
 record=[]
 for s,d in moves:
  h=sha(s); d.parent.mkdir(parents=True,exist_ok=True); shutil.move(str(s),str(d))
  if sha(d)!=h: print(f'ERROR: hash changed moving {s}'); return 1
  record.append({'from':str(s.relative_to(old)),'to':str(d.relative_to(c)),'sha256':h})
 for s,d in holdout:
  d.parent.mkdir(parents=True,exist_ok=True); shutil.move(str(s),str(d)); record.append({'from':str(s.relative_to(old)),'to':str(d.relative_to(c)),'holdout':'moved unopened'})
 rp=c/'personas/persona-registry.json'; reg=json.loads(rp.read_text()) if rp.exists() else {'personas':[]}
 for r in record:
  if r['to'].startswith('personas/versions/'):
   pid=Path(r['to']).parent.name
   if any(x['id']==pid for x in reg['personas']): print(f'ERROR: {pid} already registered'); return 1
   reg['personas'].append({'id':pid,'derived_from_audience_models':[],'versions':[{'version':'1.0','file':r['to'],'sha256':r['sha256'],'current':True,'validation_status':statuses[pid],'promoted_at':now(),'reasoning':{'migration':'Legacy flat persona moved unchanged into the versioned layout; content not edited.','legacy_path':r['from']},'evidence_delta':{}}]})
 rp.write_text(json.dumps(reg,indent=2))
 # Drop legacy placeholders and now-empty legacy folders (never anything inside an in-place holdout).
 for g in [old/'calibration/.gitkeep',old/'calibration/probes/.gitkeep',old/'personas/.gitkeep',old/'evidence/.gitkeep']+([old/'holdout/.gitkeep'] if old!=c else [])+list((old/'calibration').rglob('.DS_Store')):
  if g.exists(): g.unlink()
 for d in [old/'calibration',old/'personas',old/'evidence']+([old/'holdout'] if old!=c else []):
  if not d.is_dir(): continue
  for e in sorted((x for x in d.rglob('*') if x.is_dir()),key=lambda x:-len(x.parts))+[d]:
   if not any(e.iterdir()) and e not in (c/'evidence',c/'personas'): e.rmdir()
 mp=c/'MIGRATION.json'; log=json.loads(mp.read_text()) if mp.exists() else {'migrations':[]}
 log['migrations'].append({'migrated_at':now(),'from':str(old),'layout':'legacy-flat -> v3 client package','holdout':'not opened' if holdout else 'not touched','moves':record})
 mp.write_text(json.dumps(log,indent=2)); print(f'migrated {len(record)} files; log: {mp}'); return 0
if __name__=='__main__': raise SystemExit(main())
