#!/usr/bin/env python3
import argparse,csv,json,hashlib,datetime
from pathlib import Path
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sh(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def append(p,o):
 with p.open('a',encoding='utf-8') as f:f.write(json.dumps(o,ensure_ascii=False)+'\n')
def docx_text(p):
 from docx import Document
 return '\n'.join(x.text for x in Document(p).paragraphs if x.text.strip())
def pdf_text(p):
 from pypdf import PdfReader
 return '\n'.join((x.extract_text() or '') for x in PdfReader(p).pages)
def xlsx_rows(p):
 import openpyxl
 wb=openpyxl.load_workbook(p,read_only=True,data_only=True)
 for ws in wb.worksheets:
  it=ws.iter_rows(values_only=True)
  try:h=[str(x) if x is not None else '' for x in next(it)]
  except StopIteration:continue
  for i,row in enumerate(it,2):yield ws.title,i,{h[j]:v for j,v in enumerate(row) if j<len(h) and h[j]}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('client_dir');a=ap.parse_args();c=Path(a.client_dir);raw=c/'sources/raw';ev=c/'evidence/evidence.jsonl';regp=c/'sources/source-registry.json';bp=c/'evidence/ingestion-batches.json'
 client_config_path=c/'client.json'
 if not client_config_path.is_file():raise SystemExit(f'missing client metadata: {client_config_path}')
 client_config=json.loads(client_config_path.read_text(encoding='utf-8'))
 if not isinstance(client_config,dict):raise SystemExit(f'{client_config_path} must contain a JSON object')
 fixture=client_config.get('fixture')
 if not isinstance(fixture,bool):raise SystemExit(f'{c}/client.json must define fixture as a boolean')
 reg=json.loads(regp.read_text()) if regp.exists() else {'sources':[]};known={x['sha256'][:12] for x in reg['sources']}
 # raw sources are immutable: stop before writing anything if a registered file changed
 changed=[x['file'] for x in reg['sources'] if (c/x['file']).is_file() and not sh(c/x['file']).startswith(x['sha256'])]
 if changed:raise SystemExit('raw sources changed since registration (restore originals; add new versions as new files): '+', '.join(changed))
 bid='ING-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S');srcs=[];created=0
 for p in sorted(x for x in raw.iterdir() if x.is_file() and x.name!='.gitkeep'):
  h=sh(p)
  if h[:12] in known:continue
  sid='SRC-'+h[:12].upper();srcs.append(sid);reg['sources'].append({'id':sid,'file':str(p.relative_to(c)),'sha256':h,'file_type':p.suffix.lower().lstrip('.'),'registered_at':now(),'observed_date':None,'research_wave':None,'population':None,'method':None})
  def add(unit,typ,text=None,dims=None):
   nonlocal created;created+=1;append(ev,{'id':f'E-{bid[4:]}-{created:06d}','source_id':sid,'source_unit':str(unit),'evidence_type':typ,'text':text,'metric':None,'value':None,'base_n':None,'observed_date':None,'research_wave':None,'ingestion_batch':bid,'dimensions':dims or {},'provenance_type':'source','fixture':fixture})
  s=p.suffix.lower()
  if s in ('.txt','.md'):add('document','text',p.read_text(errors='replace'))
  elif s=='.docx':add('document','text',docx_text(p))
  elif s=='.pdf':add('document','text',pdf_text(p))
  elif s=='.csv':
   with p.open(encoding='utf-8-sig',newline='') as f:
    for i,row in enumerate(csv.DictReader(f),2):add(i,'tabular-row',json.dumps(row,ensure_ascii=False))
  elif s=='.xlsx':
   for sheet,i,row in xlsx_rows(p):add(f'{sheet}!{i}','tabular-row',json.dumps(row,ensure_ascii=False,default=str),{'sheet':sheet})
  elif s=='.json':
   obj=json.loads(p.read_text());items=obj if isinstance(obj,list) else [obj]
   for i,x in enumerate(items):add(i,'json-record',json.dumps(x,ensure_ascii=False,default=str))
  else:add('file','registered-only')
 regp.write_text(json.dumps(reg,indent=2));b=json.loads(bp.read_text()) if bp.exists() else {'batches':[]};b['batches'].append({'id':bid,'created_at':now(),'sources':srcs,'evidence_created':created,'status':'normalized-not-mapped'});bp.write_text(json.dumps(b,indent=2));print(json.dumps({'batch':bid,'sources_added':len(srcs),'evidence_created':created,'next':'review source metadata, map evidence, assess delta; personas and insights were not changed'},indent=2))
if __name__=='__main__':main()
