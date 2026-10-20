#!/usr/bin/env python3
"""Download and validate NSA PDF URLs from documents_preview.json.

Requires: pip install requests
"""
import argparse
import hashlib
import json
import logging
import os
import random
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_name(value, limit=110):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(value or 'unknown'))
    value = re.sub(r'\s+', ' ', value).strip(' .')
    return (value or 'unknown')[:limit]


def session():
    s = requests.Session()
    s.headers.update({'User-Agent': 'NSA-Exam-Crawler/1.0 (academic PDF validation)', 'Accept': 'application/pdf,*/*;q=0.8'})
    retry = Retry(total=3, connect=3, read=3, status=3, backoff_factor=1.0,
                  status_forcelist=[429, 500, 502, 503, 504], allowed_methods=['GET'],
                  respect_retry_after_header=True)
    s.mount('https://', HTTPAdapter(max_retries=retry))
    s.mount('http://', HTTPAdapter(max_retries=retry))
    return s


def valid_pdf(path):
    try:
        if path.stat().st_size < 20:
            return False, 'too_small'
        with path.open('rb') as f:
            if not f.read(1024).lstrip().startswith(b'%PDF-'):
                return False, 'not_pdf_header'
            f.seek(max(0, path.stat().st_size - 2048))
            if b'%%EOF' not in f.read():
                return False, 'missing_pdf_eof'
        return True, None
    except OSError as e:
        return False, str(e)


def checksum(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save_json_atomic(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def download_one(http, url, destination, timeout, max_mb):
    tmp = destination.with_name(destination.name + '.part')
    try:
        with http.get(url, stream=True, timeout=(timeout, timeout), allow_redirects=True) as response:
            status = response.status_code
            response.raise_for_status()
            total = 0
            with tmp.open('wb') as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_mb * 1024 * 1024:
                        raise ValueError(f'file exceeds {max_mb} MB limit')
                    f.write(chunk)
            ok, reason = valid_pdf(tmp)
            if not ok:
                raise ValueError(reason)
            os.replace(tmp, destination)
            return {'status': 'downloaded', 'http_status': status, 'bytes': total,
                    'sha256': checksum(destination), 'checked_at': utc_now()}
    except Exception as exc:
        return {'status': 'error', 'error': str(exc), 'checked_at': utc_now()}
    finally:
        tmp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', default='output/documents_preview.json')
    parser.add_argument('--out', default='output')
    parser.add_argument('--limit', type=int, default=0, help='Test first N unique URLs; 0 = all')
    parser.add_argument('--timeout', type=int, default=25)
    parser.add_argument('--max-mb', type=int, default=100)
    parser.add_argument('--delay', type=float, default=0.5, help='Seconds between requests')
    parser.add_argument('--retry-errors', action='store_true', help='Retry URLs previously recorded as errors')
    args = parser.parse_args()
    if args.limit < 0 or args.delay < 0:
        parser.error('--limit and --delay must be nonnegative')
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=output / 'download_errors.log', level=logging.WARNING,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    docs = json.loads(Path(args.input).read_text(encoding='utf-8'))
    if not isinstance(docs, list):
        parser.error('Input JSON must be a list')
    unique = {}
    for doc in docs:
        url = doc.get('source_url')
        if isinstance(url, str) and url.startswith(('https://', 'http://')):
            unique.setdefault(url, []).append(doc)
    urls = list(unique)
    if args.limit:
        urls = urls[:args.limit]
    manifest_path = output / 'download_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    http = session()
    for index, url in enumerate(urls, 1):
        previous = manifest.get(url, {})
        existing = previous.get('local_path')
        if existing and previous.get('status') in ('downloaded', 'cached'):
            existing_path = Path(existing)
            ok, _ = valid_pdf(existing_path)
            if ok and checksum(existing_path) == previous.get('sha256'):
                previous['status'] = 'cached'
                manifest[url] = previous
                print(f'[{index}/{len(urls)}] CACHED {existing_path.name}')
                continue
        if previous.get('status') == 'error' and not args.retry_errors:
            print(f'[{index}/{len(urls)}] PREVIOUS ERROR (use --retry-errors) {url}')
            continue
        doc = unique[url][0]
        kind = safe_name(doc.get('document_type'), 40)
        year = safe_name(doc.get('year'), 12)
        basename = safe_name(doc.get('filename') or Path(urlparse(url).path).name, 100)
        if not basename.lower().endswith('.pdf'):
            basename += '.pdf'
        url_id = hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]
        dest = output / 'pdfs' / kind / year / f'{url_id}_{basename}'
        dest.parent.mkdir(parents=True, exist_ok=True)
        result = download_one(http, url, dest, args.timeout, args.max_mb)
        result.update({'url': url, 'local_path': str(dest) if result['status'] == 'downloaded' else None,
                       'document_count': len(unique[url]), 'document_type': kind})
        manifest[url] = result
        if result['status'] == 'error':
            logging.warning('%s: %s', url, result['error'])
        print(f"[{index}/{len(urls)}] {result['status'].upper()} {basename}")
        save_json_atomic(manifest_path, manifest)
        if result['status'] == 'downloaded' and args.delay:
            time.sleep(args.delay)
    counts = Counter(manifest[u].get('status', 'unknown') for u in urls if u in manifest)
    summary = {'generated_at': utc_now(), 'input_documents': len(docs),
               'unique_urls_total': len(unique), 'urls_in_this_run': len(urls),
               'status_counts': dict(counts), 'manifest': str(manifest_path)}
    save_json_atomic(output / 'download_summary.json', summary)
    print('\n=== PDF DOWNLOAD SUMMARY ===')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
