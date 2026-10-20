#!/usr/bin/env python3
"""Conservative NSA metadata repair. Dry-run by default; --apply backs up and updates JSON/files."""
import argparse, collections, datetime, json, re, shutil, sys
from pathlib import Path, PureWindowsPath
from urllib.parse import urlsplit, unquote

VALID_YEARS = range(1990, 2027)

def years_in_name(name):
    # Only standalone 4-digit years; ignore numeric IDs such as 2099.
    return [int(x) for x in re.findall(r'(?<!\d)(?:19\d{2}|20\d{2})(?!\d)', name) if int(x) in VALID_YEARS]

def from_manifest_path(raw, out):
    p=Path(*PureWindowsPath(raw).parts)
    if p.is_absolute(): return p
    if p.exists(): return p
    if p.parts and p.parts[0].lower()==out.name.lower(): return out.parent/p
    return out/p

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', default='output/documents_preview.json')
    ap.add_argument('--manifest', default='output/download_manifest.json')
    ap.add_argument('--out', default='output')
    ap.add_argument('--apply', action='store_true', help='Back up, move files, and rewrite metadata')
    args=ap.parse_args()
    docpath=Path(args.input); manpath=Path(args.manifest); out=Path(args.out)
    docs=json.loads(docpath.read_text(encoding='utf-8'))
    manifest=json.loads(manpath.read_text(encoding='utf-8'))
    by_url=collections.defaultdict(list)
    for d in docs: by_url[d['source_url']].append(d)
    proposals=[]; manual=[]; conflicts=[]
    for url,entries in by_url.items():
        types={d.get('document_type') for d in entries}
        if len(types)>1: conflicts.append({'url':url,'types':sorted(types)})
        for d in entries:
            year=d.get('year')
            if not isinstance(year,int) or year in VALID_YEARS: continue
            filename=d.get('filename') or unquote(Path(urlsplit(url).path).name)
            candidates=set(years_in_name(filename))
            # Don't infer year from the URL's upload date, e.g. /2021/03/.
            if len(candidates)!=1:
                manual.append({'url':url,'old_year':year,'filename':filename,'candidate_years':sorted(candidates),'reason':'no_unique_explicit_year_in_filename'})
                continue
            newyear=next(iter(candidates))
            proposals.append({'url':url,'old_year':year,'new_year':newyear,'filename':filename,'type':d.get('document_type')})
    report={'mode':'apply' if args.apply else 'dry_run','proposed_changes':proposals,'manual_review':manual,'type_conflicts':conflicts}
    if not args.apply:
        path=out/'metadata_fix_preview.json';path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'DRY RUN: {len(proposals)} safe year corrections; {len(manual)} require manual review; {len(conflicts)} URL/type conflicts.\nReport: {path}\nRun with --apply after reviewing.')
        return
    # Validate all moves before modifying anything.
    planned_moves={}
    for item in proposals:
        m=manifest.get(item['url'])
        if not m or m.get('status') not in ('cached','downloaded') or not m.get('local_path'): continue
        src=from_manifest_path(m['local_path'],out)
        if not src.is_file(): sys.exit(f'ERROR: missing source file: {src}; nothing changed')
        if src.parent.name!=str(item['old_year']): sys.exit(f'ERROR: unexpected source folder: {src}; nothing changed')
        dst=src.parent.parent/str(item['new_year'])/src.name
        if dst.exists() and src.resolve()!=dst.resolve(): sys.exit(f'ERROR: target already exists: {dst}; nothing changed')
        planned_moves[item['url']]=(src,dst)
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup=out/f'metadata_backup_{stamp}';backup.mkdir(parents=True,exist_ok=False)
    shutil.copy2(docpath,backup/docpath.name)
    shutil.copy2(manpath,backup/manpath.name)
    moved=[]
    try:
        for url,(src,dst) in planned_moves.items():
            dst.parent.mkdir(parents=True,exist_ok=True)
            src.rename(dst);moved.append((src,dst))
            # Preserve Windows-style paths in manifest.
            manifest[url]['local_path']=str(dst).replace('/','\\')
        corrections={(p['url'],p['old_year']):p['new_year'] for p in proposals}
        for d in docs:
            key=(d['source_url'],d.get('year'))
            if key in corrections: d['year']=corrections[key]
        docpath.write_text(json.dumps(docs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        manpath.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    except Exception:
        for src,dst in reversed(moved):
            if dst.exists(): dst.rename(src)
        shutil.copy2(backup/docpath.name,docpath)
        shutil.copy2(backup/manpath.name,manpath)
        raise
    report.update({'backup':str(backup),'moved_files':len(moved)})
    path=out/'metadata_fix_report.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'APPLIED: {len(proposals)} metadata corrections, {len(moved)} files moved; {len(manual)} manual reviews; {len(conflicts)} type conflicts.\nBackup: {backup}\nReport: {path}')
    print('Next: rerun audit, then regenerate matches_v5.json using the corrected catalog.')
if __name__=='__main__': main()
