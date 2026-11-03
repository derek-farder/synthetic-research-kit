#!/usr/bin/env python3
import shutil,sys
from pathlib import Path
r=Path(__file__).resolve().parents[1]
if len(sys.argv)!=2: raise SystemExit('usage: new_study.py <study-id>')
d=r/'studies'/sys.argv[1]
if d.exists(): raise SystemExit('exists')
shutil.copytree(r/'studies'/'_template',d); print(d)
