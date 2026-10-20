#!/usr/bin/env python3
"""Audit and repair stale manifest paths using SHA-256 across the entire PDF tree."""
import argparse, hashlib, json, shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path, PureWindowsPath

def resolve(raw, out):
    p = Path(*PureWindowsPath(raw).parts)
    if p.is_absolute(): return p
    return out.parent / p if p.parts and p.parts[0].lower() == out.name.lower() else out / p

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--manifest', default='output/download_manifest.json')
    a.add_argument('--out', default='output')
    a.add_argument('--apply', action='store_true')
    args = a.parse_args()
    out, manifest_path = Path(args.out), Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    missing = [(url, rec) for url, rec in manifest.items() if rec.get('status') in ('cached','downloaded') and rec.get('local_path') and not resolve(rec['local_path'], out).is_file()]
    # Hash all files rather than filtering by filename: metadata correction can rename files.
    wanted = {r.get('sha256', '').lower() for _, r in missing if r.get('sha256')}
    by_hash = defaultdict(list)
    scanned = 0
    for p in (out / 'pdfs').rglob('*'):
        if p.is_file() and p.suffix.lower() == '.pdf':
            scanned += 1
            d = digest(p)
            if d in wanted: by_hash[d].append(p)
    fixes, unresolved = [], []
    for url, rec in missing:
        candidates = by_hash.get(str(rec.get('sha256', '')).lower(), [])
        if len(candidates) == 1:
            p = candidates[0]
            fixes.append({'url':url, 'old_path':rec['local_path'], 'new_path':str(p).replace('/', '\\'), 'sha256':rec['sha256']})
        else:
            unresolved.append({'url':url, 'old_path':rec['local_path'], 'sha256':rec.get('sha256'), 'hash_matches':len(candidates), 'reason':'not_found_in_pdf_tree' if not candidates else 'multiple_identical_files'})
    report = {'mode':'apply' if args.apply else 'dry_run', 'scanned_pdfs':scanned, 'missing_before':len(missing), 'safe_fixes':len(fixes), 'unresolved_count':len(unresolved), 'fixes':fixes, 'unresolved':unresolved}
    out.mkdir(parents=True, exist_ok=True)
    if args.apply and fixes:
        backup = out / ('download_manifest_backup_paths_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.json')
        shutil.copy2(manifest_path, backup)
        for fix in fixes: manifest[fix['url']]['local_path'] = fix['new_path']
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        report['backup'] = str(backup)
    report_path = out / 'path_repair_report_v2.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{'APPLIED' if args.apply else 'DRY RUN'}: scanned={scanned}, missing={len(missing)}, safe_fixes={len(fixes)}, unresolved={len(unresolved)}")
    for item in unresolved: print('UNRESOLVED:', item['old_path'])
    print('Report:', report_path)

if __name__ == '__main__': main()
