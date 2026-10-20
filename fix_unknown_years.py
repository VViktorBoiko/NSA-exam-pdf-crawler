#!/usr/bin/env python3
"""Set four unverified NSA exam years to null. Backup and dry-run by default."""
import argparse, json, shutil, datetime
from pathlib import Path
TARGETS = {
 '2046_Lietuviu_g_k_suvokimas_MBE_pagr.pdf': 2046,
 '2063_Matematika_VBE_I.pdf': 2063,
 '2077_Rusu-rasinys.pdf': 2077,
 '2095_11_pagr_muz_ist_teorija.pdf': 2095,
}
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',default='output/documents_preview.json');p.add_argument('--apply',action='store_true');a=p.parse_args()
 f=Path(a.input); docs=json.loads(f.read_text(encoding='utf-8'))
 changed=[]
 for d in docs:
  name=d.get('filename');year=d.get('year')
  if name in TARGETS and year==TARGETS[name]:
   changed.append((name,year,d.get('source_url')))
 if len(changed)!=4 or len({c[0] for c in changed})!=4:
  raise SystemExit(f'Expected exactly four distinct entries, found {len(changed)}; no changes made: {changed}')
 for name,year,url in changed: print(f'{year} -> null | {name}')
 if not a.apply:
  print('DRY RUN: 4 metadata corrections; run with --apply to save.');return
 backup=f.with_name(f.name+'.backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
 shutil.copy2(f,backup)
 for d in docs:
  if d.get('filename') in TARGETS and d.get('year')==TARGETS[d['filename']]:d['year']=None
 f.write_text(json.dumps(docs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'APPLIED: 4 years set to null. Backup: {backup}')
if __name__=='__main__':main()
