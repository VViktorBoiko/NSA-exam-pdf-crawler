#!/usr/bin/env python3
"""Read-only audit of all NSA PDF files and their metadata."""
import argparse, collections, hashlib, json, re
from pathlib import Path, PureWindowsPath
from datetime import datetime, timezone

KINDS = {'task','answer','review','grading_criteria','training_material','sample_task','mock_task','mock_answer','sample_answer'}

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def pdf_check(path):
    with path.open('rb') as f:
        if f.read(1024).lstrip()[:5] != b'%PDF-': return 'invalid_pdf_header'
        f.seek(max(0, path.stat().st_size - 2048))
        if b'%%EOF' not in f.read(): return 'missing_pdf_eof'
    return None

def local_path(s, root):
    # Manifest paths use Windows separators even when inspected elsewhere.
    p = Path(*PureWindowsPath(s).parts)
    if p.is_absolute(): return p
    if p.exists(): return p
    if p.parts and p.parts[0].lower() == root.name.lower(): return root.parent / p
    return root / p

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--input', default='output/documents_preview.json')
    a.add_argument('--manifest', default='output/download_manifest.json')
    a.add_argument('--out', default='output')
    args=a.parse_args()
    root=Path(args.out)
    docs=json.loads(Path(args.input).read_text(encoding='utf-8'))
    manifest=json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    by_url=collections.defaultdict(list)
    for i,d in enumerate(docs): by_url[d.get('source_url')].append((i,d))
    problems=[]; counts=collections.Counter(); by_type=collections.defaultdict(collections.Counter)
    tracked=set(); years=collections.defaultdict(set)
    def issue(code, url=None, **extra):
        counts[code]+=1
        problems.append({'problem':code,'url':url,**extra})
    for url, entries in by_url.items():
        if not url or not isinstance(url,str):
            issue('missing_url',url);continue
        m=manifest.get(url)
        if m is None:
            issue('missing_manifest_record',url);continue
        status=m.get('status')
        for _,d in entries: by_type[d.get('document_type','unknown')][status]+=1
        if len(entries)>1:
            types={d.get('document_type') for _,d in entries}
            if len(types)>1: issue('same_url_multiple_types',url,types=sorted(map(str,types)))
        if status=='error':
            issue('download_error',url,error=m.get('error'),http_status=m.get('http_status'))
            continue
        if status not in ('cached','downloaded'):
            issue('unknown_manifest_status',url,status=status);continue
        raw=m.get('local_path')
        if not raw:
            issue('missing_local_path',url);continue
        p=local_path(raw,root)
        tracked.add(str(p.resolve()))
        if not p.is_file():
            issue('file_missing',url,path=str(p));continue
        counts['files_present']+=1
        try:
            if p.stat().st_size!=m.get('bytes'): issue('size_mismatch',url,path=str(p),actual=p.stat().st_size,expected=m.get('bytes'))
            if (reason:=pdf_check(p)): issue(reason,url,path=str(p))
            if digest(p)!=m.get('sha256'): issue('sha256_mismatch',url,path=str(p))
            else: counts['hash_verified']+=1
        except OSError as e: issue('file_read_error',url,path=str(p),error=str(e))
        expected_type=entries[0][1].get('document_type') or 'unknown'
        expected_year=str(entries[0][1].get('year') or 'unknown')
        years[expected_type].add(expected_year)
        if p.parent.name!=expected_year: issue('year_folder_vs_metadata',url,path=str(p),expected_year=expected_year,actual_folder=p.parent.name)
        if p.parent.parent.name!=expected_type: issue('type_folder_vs_metadata',url,path=str(p),expected_type=expected_type,actual_folder=p.parent.parent.name)
        if expected_type not in KINDS: issue('unexpected_document_type',url,type=expected_type)
        year_value=entries[0][1].get('year')
        if isinstance(year_value,int) and (year_value>2026 or year_value<1990):
            issue('suspicious_year',url,year=year_value,filename=entries[0][1].get('filename'),path=str(p))
        if m.get('document_count')!=len(entries): issue('document_count_mismatch',url,expected=len(entries),recorded=m.get('document_count'))
    for url in manifest:
        if url not in by_url: issue('manifest_url_not_in_catalog',url)
    pdfroot=root/'pdfs'
    actual=set()
    if pdfroot.exists():
        for p in pdfroot.rglob('*'):
            if p.is_file() and not p.name.endswith('.part'):
                actual.add(str(p.resolve()))
                if str(p.resolve()) not in tracked: issue('untracked_file',path=str(p))
    else: issue('pdf_directory_missing',path=str(pdfroot))
    report={'generated_at':datetime.now(timezone.utc).isoformat(), 'input_documents':len(docs),
            'catalog_unique_urls':len(by_url),'manifest_records':len(manifest),
            'files_on_disk':len(actual),'files_tracked_on_disk':len(actual & tracked),
            'by_document_type':{k:dict(v) for k,v in sorted(by_type.items())},
            'years_by_type':{k:sorted(v) for k,v in sorted(years.items())},
            'problem_counts':dict(sorted(counts.items())), 'problems':problems}
    target=root/'archive_audit.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('=== NSA ARCHIVE AUDIT ===')
    print(f"Catalog: {len(docs)} documents / {len(by_url)} URLs")
    print(f"Manifest: {len(manifest)} URLs | Local files: {len(actual)} | Verified SHA256: {counts['hash_verified']}")
    print('Document types:',json.dumps(report['by_document_type'],ensure_ascii=False))
    print('Issues:',json.dumps(report['problem_counts'],ensure_ascii=False))
    print('Report:',target)
    print('NOTE: suspicious_year indicates metadata requiring review, not a proven wrong year.')

if __name__=='__main__':main()
