#!/usr/bin/env python3
import argparse,sys,re,datetime
from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check_study import check
HEADER='SIMULATED RESEARCH - HYPOTHESES, NOT FINDINGS'
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('study'); ap.add_argument('--out'); ap.add_argument('--allow-unreviewed',action='store_true'); ap.add_argument('--client'); a=ap.parse_args(); study=Path(a.study).resolve(); w,e=check(study,a.client)
 if e: [print('ERROR:',x) for x in e]; return 1
 reviewed=(study/'skeptic-review.md').exists()
 if not reviewed and not a.allow_unreviewed: print('ERROR: skeptic review missing'); return 1
 src=(study/'synthesis.md').read_text(); out=Path(a.out) if a.out else study/'export'/f'{study.name}-synthesis.docx'; out.parent.mkdir(parents=True,exist_ok=True)
 d=Document(); sec=d.sections[0]; hp=sec.header.paragraphs[0]; hp.text=HEADER; hp.alignment=WD_ALIGN_PARAGRAPH.CENTER
 for r in hp.runs:r.font.color.rgb=RGBColor(192,0,0); r.bold=True
 fp=sec.footer.paragraphs[0]; fp.text=f'{study.name} | {datetime.date.today().isoformat()} | Page '; fp.add_run().add_field if False else None
 title=next((x[2:].strip() for x in src.splitlines() if x.startswith('# ')),'Synthetic Research Synthesis'); d.add_heading(title,0)
 p=d.add_paragraph('Everything in this document comes from language-model personas, not from research participants. Treat it as hypotheses to test with real people. Do not quote it as participant feedback, and do not put it in a client deliverable without this framing.')
 p.style='Intense Quote'; d.add_paragraph('Skeptic review: '+('DONE' if reviewed else 'NOT DONE'))
 for line in src.splitlines():
  if line.startswith('# '): continue
  if line.startswith('## '): d.add_heading(line[3:],1)
  elif line.startswith('### '): d.add_heading(line[4:],2)
  elif line.startswith('> '): d.add_paragraph(line[2:],style='Quote')
  elif re.match(r'^[-*] ',line): d.add_paragraph(line[2:],style='List Bullet')
  elif line.strip(): d.add_paragraph(line)
 d.save(out)
 d2=Document(out); full='\n'.join(p.text for p in d2.paragraphs)+'\n'+'\n'.join(p.text for s in d2.sections for p in list(s.header.paragraphs)+list(s.footer.paragraphs))
 tags=re.findall(r'\[(?:SYN|REAL|support):[^\]]+\]',src,re.I); missing=[t for t in set(tags) if full.count(t)<tags.count(t)]
 if HEADER not in full or missing or (not reviewed and 'NOT DONE' not in full): out.unlink(missing_ok=True); print('ERROR: verification failed',missing); return 1
 print(f'VERIFIED: {len(tags)} provenance/support tags; wrote {out}'); return 0
if __name__=='__main__': raise SystemExit(main())
