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
PROVENANCE_TYPES = {'source', 'derived', 'analytical', 'simulation'}

def _client_fixture(path):
    p = Path(path)
    if p.is_file():
        p = p.parent
    client_config = p.parent / 'client.json' if p.name == 'evidence' else p / 'client.json'
    if not client_config.exists():
        return False
    config = json.loads(client_config.read_text(encoding='utf-8'))
    fixture = config.get('fixture')
    if not isinstance(fixture, bool):
        raise ValueError(f'{client_config}: fixture must be a boolean')
    return fixture

def _record_provenance(record):
    provenance_type = record.get('provenance_type')
    legacy = False
    if provenance_type is None:
        legacy = True
        if isinstance(record.get('synthetic'), bool):
            provenance_type = 'simulation' if record['synthetic'] else 'source'
        elif isinstance(record, str):
            provenance_type = 'source'
    if provenance_type not in PROVENANCE_TYPES:
        provenance_type = 'unknown'
    return provenance_type, legacy

def _load_evidence_file(path, fixture_default=False):
    path=Path(path)
    if path.suffix=='.jsonl':
        # v3 normalized evidence records (schemas/evidence-record.schema.json)
        out={}
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                r=json.loads(line)
                provenance_type, legacy = _record_provenance(r)
                fixture = r.get('fixture', fixture_default)
                if not isinstance(fixture, bool):
                    raise ValueError(f"{path}: evidence {r['id']} fixture must be a boolean")
                out[r['id']]={
                    'quote':r.get('text') or '',
                    'source':r.get('source_id','unknown'),
                    'provenance_type':provenance_type,
                    'fixture':fixture,
                    'source_lineage':r.get('source_lineage', []),
                    'derivation_method':r.get('derivation_method'),
                    'scope':r.get('scope'),
                    'legacy_provenance':legacy,
                }
        return out
    data=json.loads(path.read_text(encoding='utf-8'))
    out={}
    for key, value in data.items():
        if key.startswith('_'):
            continue
        record={'quote':value,'source':'unknown','synthetic':False} if isinstance(value,str) else dict(value)
        provenance_type, legacy = _record_provenance(record)
        fixture=record.get('fixture', fixture_default)
        if not isinstance(fixture, bool):
            raise ValueError(f"{path}: evidence {key} fixture must be a boolean")
        out[key]={
            **record,
            'provenance_type':provenance_type,
            'fixture':fixture,
            'source_lineage':record.get('source_lineage', []),
            'derivation_method':record.get('derivation_method'),
            'scope':record.get('scope'),
            'legacy_provenance':legacy,
        }
    return out

def _traceable_lineage(record_id, evidence, visiting=None):
    visiting=set() if visiting is None else visiting
    if record_id in visiting:
        return False, f'cyclic source lineage at {record_id}'
    record=evidence.get(record_id)
    if record is None:
        return False, f'missing lineage record {record_id}'
    provenance_type=record.get('provenance_type')
    if provenance_type=='source':
        return True, None
    if provenance_type!='derived':
        return False, f'lineage record {record_id} has ineligible provenance_type {provenance_type}'
    lineage=record.get('source_lineage')
    if not isinstance(lineage,list) or not lineage:
        return False, f'derived record {record_id} has no source_lineage'
    if not record.get('derivation_method'):
        return False, f'derived record {record_id} has no derivation_method'
    if not record.get('scope'):
        return False, f'derived record {record_id} has no scope'
    visiting.add(record_id)
    for parent_id in lineage:
        if not isinstance(parent_id,str):
            visiting.remove(record_id)
            return False, f'derived record {record_id} has a non-string source_lineage entry'
        eligible, reason=_traceable_lineage(parent_id,evidence,visiting)
        if not eligible:
            visiting.remove(record_id)
            return False, reason
    visiting.remove(record_id)
    return True, None

def _resolve_grounding_eligibility(evidence):
    for record_id, record in evidence.items():
        provenance_type=record.get('provenance_type')
        if provenance_type=='source':
            record['lineage_valid']=True
            record['grounding_eligible']=True
            record['eligibility_reason']='source evidence is eligible; fixture status does not affect eligibility'
        elif provenance_type=='derived':
            lineage=record.get('source_lineage')
            valid, reason = (False, 'derived evidence has no source_lineage') if not isinstance(lineage,list) or not lineage else (True, None)
            if valid and not record.get('derivation_method'):
                valid, reason=False, 'derived evidence has no derivation_method'
            if valid and not record.get('scope'):
                valid, reason=False, 'derived evidence has no scope'
            if valid:
                for parent_id in lineage:
                    if not isinstance(parent_id,str):
                        valid, reason=False, 'derived evidence has a non-string source_lineage entry'
                        break
                    valid, reason=_traceable_lineage(parent_id,evidence,{record_id})
                    if not valid:
                        break
            record['lineage_valid']=valid
            record['grounding_eligible']=valid
            record['eligibility_reason']=reason or 'derived evidence has traceable source lineage; claim must remain within its documented scope'
        elif provenance_type=='analytical':
            lineage=record.get('source_lineage')
            valid, reason = (False, 'analytical evidence has no source_lineage') if not isinstance(lineage,list) or not lineage else (True, None)
            if valid:
                for parent_id in lineage:
                    if not isinstance(parent_id,str):
                        valid, reason=False, 'analytical evidence has a non-string source_lineage entry'
                        break
                    valid, reason=_traceable_lineage(parent_id,evidence,{record_id})
                    if not valid:
                        break
            record['lineage_valid']=valid
            record['grounding_eligible']=False
            record['eligibility_reason']=reason or 'analytical evidence is not eligible as primary grounding'
        else:
            record['lineage_valid']=False
            record['grounding_eligible']=False
            record['eligibility_reason']='simulation evidence is never eligible for persona grounding' if provenance_type=='simulation' else f'unknown provenance_type {provenance_type!r}'

def load_evidence(path):
    """Load evidence.json, evidence.jsonl, or a client evidence/ directory holding either or both."""
    p=Path(path)
    fixture_default=_client_fixture(p)
    if not p.is_dir():
        out=_load_evidence_file(p,fixture_default)
        _resolve_grounding_eligibility(out)
        return out
    out={}
    for f in (p/'evidence.json',p/'evidence.jsonl'):
        if f.exists():
            for k,v in _load_evidence_file(f,fixture_default).items():
                if k in out: raise ValueError(f'duplicate evidence id {k} in {p}')
                out[k]=v
    _resolve_grounding_eligibility(out)
    return out
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
    legacy_reported=set()
    for i,c in enumerate(persona['claims'],1):
        if c['category']!='context': behavioral+=1
        if not c['evidence']: issues.append({'level':'WARN','code':'UNGROUNDED','message':f'Claim {i} has no evidence'})
        for eid in c['evidence']:
            if eid not in evidence: issues.append({'level':'ERROR','code':'MISSING_EVIDENCE','message':f'Claim {i} cites missing {eid}'})
            else:
                if evidence[eid].get('legacy_provenance') and eid not in legacy_reported:
                    issues.append({'level':'WARN','code':'LEGACY_PROVENANCE','message':f'Evidence {eid} uses legacy synthetic provenance; migrate it to provenance_type and fixture'})
                    legacy_reported.add(eid)
                if not evidence[eid].get('grounding_eligible',False):
                    issues.append({'level':'ERROR','code':'INELIGIBLE_EVIDENCE','message':f"Claim {i} cites ineligible evidence {eid}: {evidence[eid].get('eligibility_reason','unknown eligibility')}"})
                elif evidence[eid].get('provenance_type')=='derived':
                    issues.append({'level':'WARN','code':'DERIVED_SCOPE_REVIEW','message':f"Claim {i} must stay within the scope of derived evidence {eid}: {evidence[eid].get('scope')}"})
    if behavioral<3: issues.append({'level':'WARN','code':'FEW_BEHAVIORAL','message':'Fewer than three behavioral claims'})
    n=len(persona['claims']) or 1
    grounded=sum(bool(c['evidence']) and all(e in evidence and evidence[e].get('grounding_eligible',False) for e in c['evidence']) for c in persona['claims'])/n
    thick=sum(len([e for e in c['evidence'] if e in evidence and evidence[e].get('grounding_eligible',False)])>=2 for c in persona['claims'])/n
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
