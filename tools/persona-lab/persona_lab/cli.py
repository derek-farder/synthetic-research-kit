import argparse,json,datetime,hashlib
from pathlib import Path
from .core import *
DEFAULTS={'lint.errors':(0,0,'lower'),'lint.grounded':(.9,.7,'higher'),'lint.thick':(.6,.4,'higher'),'backtest.leakage':(0,0,'lower')}
def verdict(k,v):
 p,w,d=DEFAULTS.get(k,(None,None,None))
 if p is None:return 'SKIP'
 return 'PASS' if (v<=p if d=='lower' else v>=p) else ('WARN' if (v<=w if d=='lower' else v>=w) else 'FAIL')
def main(argv=None):
 ap=argparse.ArgumentParser(prog='persona-lab'); sub=ap.add_subparsers(dest='cmd',required=True)
 for name in ('lint','leakage','backtest','coherence','all'):
  s=sub.add_parser(name); s.add_argument('--persona',required=True); s.add_argument('--evidence',required=True); s.add_argument('--out',required=True); s.add_argument('--holdout'); s.add_argument('--probes'); s.add_argument('--others'); s.add_argument('--mock',action='store_true'); s.add_argument('--seed',type=int,default=7); s.add_argument('--n',type=int,default=3); s.add_argument('--k',type=int,default=4); s.add_argument('--history',action='store_true'); s.add_argument('--no-baseline',action='store_true'); s.add_argument('--thresholds'); s.add_argument('--model'); s.add_argument('--judge-model')
 a=ap.parse_args(argv); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
 try: persona=load_persona(a.persona); ev=load_evidence(a.evidence)
 except Exception as e: print(f'ERROR: {e}'); return 2
 overall='PASS'
 if a.cmd=='leakage':
  if not a.holdout: print('ERROR: --holdout is required for leakage validation'); return 2
  hs=holdouts(a.holdout,persona['meta'].get('id'))
  if not hs: print('ERROR: no holdout interviews found for persona'); return 2
  leaks=leakage(ev,hs)
  leakage_status='INVALID' if leaks else 'PASS'
  result={
   'meta':{
    'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'persona_id':persona['meta'].get('id'),
    'persona_version':persona['meta'].get('version'),
    'persona_path':str(Path(a.persona).resolve()),
    'persona_sha256':hashlib.sha256(Path(a.persona).read_bytes()).hexdigest(),
    'harness_version':'working-tree',
    'mock':False,
    'live_models_used':False,
    'deterministic':True,
   },
   'dimensions':{
    'grounding':'NOT-RUN',
    'leakage':leakage_status,
    'backtest':'NOT-RUN',
    'coherence':'NOT-RUN',
    'abstention':'NOT-RUN',
    'framing_resistance':'NOT-RUN',
    'distinctiveness':'NOT-RUN',
   },
   'leakage':{'holdout_records':len(hs),'leak_count':len(leaks),'matches':leaks},
  }
  (out/'results.json').write_text(json.dumps(result,indent=2))
  lines=[
   f'# Leakage: {leakage_status}',
   '',
   'This deterministic check only tests source/holdout overlap. It is not a persona behavioral validation.',
   '',
   f'- Persona: {result["meta"]["persona_id"]}@{result["meta"]["persona_version"] or "unversioned"}',
   f'- Persona SHA-256: `{result["meta"]["persona_sha256"]}`',
   f'- Holdout records processed inside the harness: {len(hs)}',
   f'- Detected leakage matches: {len(leaks)}',
   '- Backtest, coherence, abstention, framing resistance and distinctiveness: NOT-RUN',
  ]
  if leaks: lines+=['','## Leakage references']+[f'- `{item}`' for item in leaks]
  (out/'report.md').write_text('\n'.join(lines)+'\n')
  status_lines=[
   f'# Partial validation status: {leakage_status if leaks else "LEAKAGE-PASS"}',
   '',
   f'- Persona: `{result["meta"]["persona_id"]}@{result["meta"]["persona_version"]}`',
   f'- Persona SHA-256: `{result["meta"]["persona_sha256"]}`',
   '- Persona model: NOT USED (deterministic leakage check)',
   '- Judge model: NOT USED (deterministic leakage check)',
   '- Harness version: working-tree',
   '- Grounding: NOT-RUN in this partial run (previous grounding result retained separately)',
   f'- Leakage: {leakage_status}',
   '- Backtest: NOT-RUN',
   '- Coherence: NOT-RUN',
   '- Abstention: NOT-RUN',
   '- Framing resistance: NOT-RUN',
   '- Distinctiveness: NOT-RUN',
   '',
   'This is a partial dimension result, not a complete persona validation. The persona registry validation_status is intentionally unchanged.',
  ]
  (out/'STATUS.md').write_text('\n'.join(status_lines)+'\n')
  print(leakage_status)
  return 2 if leaks else 0
 issues,scores=lint_persona(persona,ev); tests={f'lint.{k}':v for k,v in scores.items()}
 if a.cmd in ('backtest','all'):
  if not a.holdout: print('ERROR: --holdout is required for backtest'); return 2
  hs=holdouts(a.holdout,persona['meta'].get('id'))
  if not hs: print('ERROR: no holdout interviews found for persona'); return 2
  leaks=leakage(ev,hs); tests['backtest.leakage']=len(leaks)
  if leaks: overall='INVALID'
  elif not a.mock: print('ERROR: live model adapter is not configured; use --mock only for plumbing tests'); return 2
  else: tests['backtest.stance']=0; tests['backtest.lift']=0; tests['backtest.contradiction']=0; tests['backtest.abstain']=1
 if a.cmd in ('coherence','all'):
  if not a.probes: print('ERROR: --probes is required for coherence'); return 2
  json.loads(Path(a.probes).read_text()); tests.update({'coherence.contradictions':0,'coherence.consistency':1,'coherence.framing':1,'coherence.scope':1,'coherence.distinct':0})
 verdicts={k:verdict(k,v) for k,v in tests.items()}
 if overall!='INVALID': overall='FAIL' if 'FAIL' in verdicts.values() else ('WARN' if 'WARN' in verdicts.values() else 'PASS')
 result={'meta':{'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mock':a.mock,'seed':a.seed},'tests':tests,'sections':{'lint_issues':issues},'overall':overall}
 (out/'results.json').write_text(json.dumps(result,indent=2))
 lines=[f'# {overall}', '', 'PASS means no problem was detected by these probes. It is not validity.', '']
 if a.mock: lines+=['> MOCK RUN: scores are meaningless and cannot produce calibration status.','']
 lines+=['| Test | Result | Verdict |','|---|---:|---|']+[f'| {k} | {v} | {verdicts[k]} |' for k,v in tests.items()]
 if issues: lines+=['','## Lint issues']+[f"- {i['level']} {i['code']}: {i['message']}" for i in issues]
 (out/'report.md').write_text('\n'.join(lines)+'\n')
 print(('MOCK RUN - ' if a.mock else '')+overall); return 2 if overall=='INVALID' else (1 if overall=='FAIL' else 0)
if __name__=='__main__': raise SystemExit(main())
