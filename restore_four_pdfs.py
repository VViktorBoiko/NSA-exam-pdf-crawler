#!/usr/bin/env python3
"""Restore exactly four missing PDFs; verify against the original manifest SHA-256."""
import argparse, hashlib, json, shutil
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
import requests

NAMES = ('2046_Lietuviu_g_k_suvokimas_MBE_pagr.pdf', '2063_Matematika_VBE_I.pdf', '2077_Rusu-rasinys.pdf', '2095_11_pagr_muz_ist_teorija.pdf')

def path_from_manifest(raw, out):
    p = Path(*PureWindowsPath(raw).parts)
    return (out.parent / p) if p.parts and p.parts[0].lower() == out.name.lower() else (out / p)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default='output/download_manifest.json')
    parser.add_argument('--out', default='output')
    args = parser.parse_args()
    out, mf = Path(args.out), Path(args.manifest)
    data = json.loads(mf.read_text(encoding='utf-8'))
    records = [(url, rec) for url, rec in data.items() if any(url.endswith('/' + name) for name in NAMES)]
    if len(records) != 4:
        raise SystemExit(f'Expected exactly 4 manifest entries, got {len(records)}; no changes made.')
    report = []
    changed = False
    session = requests.Session()
    session.headers['User-Agent'] = 'NSA-Exam-Crawler/1.0 (PDF archive validation)'
    for url, rec in records:
        old = path_from_manifest(rec['local_path'], out)
        if old.is_file():
            report.append({'url':url, 'result':'already_present', 'path':str(old)})
            continue
        # Keep historical filename and place recovered documents in unknown year,
        # rather than restoring an obviously incorrect 20xx directory.
        target = out / 'pdfs' / 'task' / 'unknown' / old.name
        tmp = target.with_suffix('.part')
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with session.get(url, timeout=(15, 90), stream=True, allow_redirects=True) as resp:
                resp.raise_for_status()
                h = hashlib.sha256()
                size = 0
                with tmp.open('wb') as fh:
                    first = b''
                    for chunk in resp.iter_content(chunk_size=262144):
                        if not chunk: continue
                        if not first: first = chunk[:1024]
                        h.update(chunk); size += len(chunk); fh.write(chunk)
                if not first.lstrip().startswith(b'%PDF-'):
                    raise ValueError('Response is not a PDF')
                if h.hexdigest().lower() != rec['sha256'].lower():
                    raise ValueError('SHA-256 differs from previously downloaded PDF; refusing replacement')
                if target.exists():
                    raise ValueError('Target already exists; refusing overwrite')
                tmp.replace(target)
                rec['local_path'] = str(target).replace('/', '\\')
                rec['bytes'] = size
                rec['checked_at'] = datetime.now(timezone.utc).isoformat()
                changed = True
                report.append({'url':url, 'result':'restored', 'path':str(target), 'sha256':h.hexdigest()})
        except Exception as exc:
            report.append({'url':url, 'result':'unavailable', 'error':str(exc)})
        finally:
            tmp.unlink(missing_ok=True)
    if changed:
        backup = mf.with_name('download_manifest_backup_restore_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.json')
        shutil.copy2(mf, backup)
        mf.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Manifest backup:', backup)
    report_path = out / 'restore_four_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for entry in report:
        print(entry['result'].upper(), entry['url'].split('/')[-1], entry.get('error',''))
    print('Report:', report_path)

if __name__ == '__main__':
    main()
