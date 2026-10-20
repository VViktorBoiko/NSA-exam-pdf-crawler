#!/usr/bin/env python3
"""Build task-centric NSA dataset from frozen matcher and downloader outputs."""
import argparse
import collections
import datetime
import json
from pathlib import Path

SUCCESS = {'cached', 'downloaded', 'restored'}
FIELDS = ('year', 'subject', 'exam_type', 'session', 'srautas', 'dalis', 'level')

def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def state(url, manifest):
    if not url:
        return {'url': None, 'local_path': None, 'download_status': 'not_selected', 'sha256': None, 'error': None, 'available': False}
    m = manifest.get(url)
    if m is None:
        return {'url': url, 'local_path': None, 'download_status': 'not_in_manifest', 'sha256': None, 'error': 'URL absent from manifest', 'available': False}
    status = m.get('status')
    return {'url': url, 'local_path': m.get('local_path'), 'download_status': status, 'sha256': m.get('sha256'), 'error': m.get('error'), 'available': status in SUCCESS and bool(m.get('local_path'))}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', default='output/documents_preview.json')
    p.add_argument('--matches', default='output/matches_v5.json')
    p.add_argument('--manifest', default='output/download_manifest.json')
    p.add_argument('--out', default='output')
    a = p.parse_args()
    catalog, matches, manifest = load(a.input), load(a.matches), load(a.manifest)
    if not isinstance(catalog, list) or not isinstance(matches, list) or not isinstance(manifest, dict):
        p.error('Unexpected JSON format: catalog/matches must be lists and manifest an URL-keyed object')
    task_urls = {d.get('source_url') for d in catalog if d.get('document_type') == 'task'}
    if len(matches) != sum(d.get('document_type') == 'task' for d in catalog):
        p.error('Task count mismatch between catalog and matcher. Rerun Matching V5 on corrected catalog.')
    if any(m.get('task_source_url') not in task_urls for m in matches):
        p.error('Matcher contains task URLs absent from the catalog.')
    if len({m.get('task_source_url') for m in matches}) != len(matches):
        p.error('Duplicate task URL in matcher; cannot safely generate unique task records.')
    result = []
    for i, m in enumerate(matches, 1):
        task = state(m.get('task_source_url'), manifest)
        chosen = m.get('answer_source_url') if m.get('match_status') == 'provisional' else None
        answer = state(chosen, manifest)
        if not task['available']:
            final_status, reason = 'broken_link', 'Task PDF unavailable'
        elif m.get('match_status') == 'provisional' and not answer['available']:
            final_status, reason = 'broken_link', 'Selected answer PDF unavailable'
        elif m.get('match_status') == 'provisional':
            final_status, reason = 'found', 'Metadata-only provisional match; PDF contents not compared'
        else:
            final_status, reason = 'missing', ('No compatible instruction candidate' if m.get('match_status') == 'no_candidate' else 'Candidate(s) require review; no instruction selected')
        candidates = []
        for c in m.get('top_candidates', []):
            candidate = dict(c)
            candidate['download'] = state(c.get('answer_source_url'), manifest)
            candidates.append(candidate)
        result.append({
            'id': i,
            **{k: m.get(k) for k in FIELDS},
            'task_filename': m.get('task_filename'),
            'task': task,
            'answer_filename': m.get('answer_filename') if chosen else None,
            'answer': answer,
            'status': final_status,
            'status_reason': reason,
            'match_status': m.get('match_status'),
            'match_verified_by_pdf_content': False,
            'review_required': m.get('match_status') != 'no_candidate',
            'review_reason': m.get('review_reason'),
            'best_score': m.get('best_score'),
            'candidate_count': m.get('candidate_count'),
            'top_candidates': candidates,
        })
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'tasks': len(result),
        'status_counts': dict(collections.Counter(x['status'] for x in result)),
        'match_status_counts': dict(collections.Counter(x['match_status'] for x in result)),
        'provisional_found_count': sum(x['status'] == 'found' for x in result),
        'note': 'found means accessible metadata-based provisional match, NOT content-verified; missing includes unresolved review candidates',
    }
    (out/'final_dataset.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (out/'final_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print('=== FINAL DATASET ===')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('Saved:', out/'final_dataset.json', 'and', out/'final_summary.json')

if __name__ == '__main__':
    main()
