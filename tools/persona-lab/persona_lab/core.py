import re,json,hashlib,random,statistics
from pathlib import Path
CLAIM_RE=re.compile(r'^- \[([^\]]*)\]\s*(?:(behavior|workaround|constraint|distrust|goal|context):\s*)?(.*)$')
def frontmatter(text):
    if not text.startswith('---\n'): return {},text
    _,fm,body=text.split('---',2); d={}
    for line in fm.splitlines():
        if ':' in line:
            k,v=line.split(':',1); d[k.strip()]=v.strip()
    return d,body.lstrip('\n')
def load_evidence(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    return {k:({'quote':v,'source':'unknown','synthetic':False} if isinstance(v,str) else v) for k,v in data.items() if not k.startswith('_')}
def load_persona(path):
    text=Path(path).read_text(encoding='utf-8'); fm,body=frontmatter(text); claims=[]
    sec=False; profile=[]; inprof=False
    for line in body.splitlines():
        if line.strip()=='## Profile': inprof=True; sec=False; continue
        if line.strip()=='## Claims': sec=True; inprof=False; continue
        if inprof and line and not line.startswith('#'): profile.append(line.strip())
        if sec:
            m=CLAIM_RE.match(line.strip())
            if m: claims.append({'evidence':[x.strip() for x in m.group(1).split(',') if x.strip()],'category':m.group(2),'text':m.group(3)})
    return {'meta':fm,'role':fm.get('role','participant'),'profile':' '.join(profile),'claims':claims,'text':text}
def lint_persona(persona,evidence):
    issues=[]
    if not persona['claims']: issues.append({'level':'ERROR','code':'NO_CLAIMS','message':'Persona has no claims'})
    behavioral=0
    for i,c in enumerate(persona['claims'],1):
        if c['category']!='context': behavioral+=1
        if not c['evidence']: issues.append({'level':'WARN','code':'UNGROUNDED','message':f'Claim {i} has no evidence'})
        for eid in c['evidence']:
            if eid not in evidence: issues.append({'level':'ERROR','code':'MISSING_EVIDENCE','message':f'Claim {i} cites missing {eid}'})
            elif evidence[eid].get('synthetic'): issues.append({'level':'ERROR','code':'SYNTHETIC_EVIDENCE','message':f'Claim {i} cites synthetic {eid}'})
    if behavioral<3: issues.append({'level':'WARN','code':'FEW_BEHAVIORAL','message':'Fewer than three behavioral claims'})
    n=len(persona['claims']) or 1
    grounded=sum(bool(c['evidence']) and all(e in evidence and not evidence[e].get('synthetic') for e in c['evidence']) for c in persona['claims'])/n
    thick=sum(len([e for e in c['evidence'] if e in evidence and not evidence[e].get('synthetic')])>=2 for c in persona['claims'])/n
    return issues,{'errors':sum(x['level']=='ERROR' for x in issues),'grounded':grounded,'thick':thick}
def holdouts(path,persona_id=None):
    p=Path(path); files=[p] if p.is_file() else sorted(p.glob('*.json')); out=[]
    for f in files:
        x=json.loads(f.read_text()); xs=x if isinstance(x,list) else [x]
        out.extend(i for i in xs if i.get('persona_id') in (None,persona_id))
    return out
def leakage(evidence,hs):
    leaks=[]
    sources={str(v.get('source','')) for v in evidence.values()}
    for h in hs:
        if h.get('id') in sources: leaks.append('source:'+h['id'])
        for t in h.get('turns',[]):
            a=re.findall(r"[a-z0-9']+",t.get('a','').lower())
            grams={' '.join(a[i:i+6]) for i in range(max(0,len(a)-5))}
            for eid,e in evidence.items():
                q=re.findall(r"[a-z0-9']+",e.get('quote','').lower())
                eg={' '.join(q[i:i+6]) for i in range(max(0,len(q)-5))}
                if grams & eg: leaks.append(f'text:{eid}:{h.get("id")}')
    return sorted(set(leaks))
def mock_answer(persona,q):
    words=set(re.findall(r'[a-z]+',q.lower())); ranked=sorted(persona['claims'],key=lambda c:len(words & set(re.findall(r'[a-z]+',c['text'].lower()))),reverse=True)
    if ranked and len(words & set(re.findall(r'[a-z]+',ranked[0]['text'].lower()))): return ranked[0]['text']
    return "I haven't dealt with that directly, so I'm not sure."
