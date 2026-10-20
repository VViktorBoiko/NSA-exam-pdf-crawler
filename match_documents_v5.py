"""Conservative NSA task/answer metadata matcher V5.

Usage: python match_documents_v5.py --input output/documents_preview.json --out output
No PDF content is downloaded or validated by this script.
"""
import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

FIELDS = ('year', 'subject', 'exam_type', 'session', 'srautas', 'dalis', 'level')
WEIGHTS = {'year': 35, 'subject': 35, 'exam_type': 5, 'session': 15,
           'srautas': 10, 'dalis': 15, 'level': 10}

def norm(value):
    if value is None:
        return ''
    s = unicodedata.normalize('NFKD', str(value)).lower()
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in s if not unicodedata.combining(c))).strip()

def filename_part(name):
    m = re.search(r'\bvbe\s*(ii|2|i|1)\b', norm(name))
    return ('II' if m.group(1) in ('ii', '2') else 'I') if m else None

def filename_session(name):
    s = norm(name)
    if re.search(r'\b(pk|pak|pakartotine|pakartotinis|pakartotines)\b', s):
        return 'pakartotinė'
    if re.search(r'\b(pg|pagr|pagrindine|pagrindinis|pagrindines)\b', s):
        return 'pagrindinė'
    return None

def filename_level(name):
    s = norm(name)
    # Only A/B near VBE or its part: avoid arbitrary letters elsewhere in names.
    m = re.search(r'\bvbe\s*(?:ii|2|i|1)?\s*([ab])\b', s)
    if m:
        return 'išplėstinis' if m.group(1) == 'a' else 'bendrasis'
    # PG-A, PK-B patterns, often in Lithuanian language exams.
    m = re.search(r'\b(?:pg|pk|pak)\s*([ab])\b', s)
    return ('išplėstinis' if m.group(1) == 'a' else 'bendrasis') if m else None

def meta(doc):
    m = {k: doc.get(k) for k in FIELDS}
    conflicts = []
    for field, inferred in (('dalis', filename_part(doc.get('filename'))),
                            ('session', filename_session(doc.get('filename'))),
                            ('level', filename_level(doc.get('filename')))):
        if inferred:
            if m[field] is not None and norm(m[field]) != norm(inferred):
                conflicts.append(field)
            else:
                m[field] = inferred
    return m, conflicts

def compare(tm, am, answer):
    matched, unknown = [], []
    for field in FIELDS:
        a, b = tm[field], am[field]
        if a is not None and b is not None:
            if norm(a) != norm(b):
                return None
            matched.append(field)
        else:
            unknown.append(field)
    if not {'year', 'subject'}.issubset(matched):
        return None
    return {'answer_filename': answer.get('filename'),
            'answer_source_url': answer.get('source_url'),
            'score': sum(WEIGHTS[k] for k in matched),
            'matched_fields': matched, 'unknown_fields': unknown,
            'answer_session': am['session'], 'answer_level': am['level'],
            'answer_part': am['dalis']}

def decide(task_meta, candidates):
    if not candidates:
        return 'no_candidate', None, 'No compatible metadata candidate'
    top = candidates[0]['score']
    close = [c for c in candidates if top - c['score'] < 10]
    # A single candidate is still unverified when its session is known but task session isn't.
    if task_meta['session'] is None and any(c['answer_session'] is not None for c in candidates):
        return 'session_review', None, 'Task session unknown; cannot verify answer session'
    if len(close) > 1:
        signatures = {(norm(c['answer_session']), norm(c['answer_level']), norm(c['answer_part'])) for c in close}
        if len(signatures) == 1:
            return 'version_review', None, 'Multiple equally plausible instruction files'
        return 'ambiguous', None, 'Multiple competing metadata candidates'
    # A clear top candidate still requires review when another candidate is a plausible
    # version of the same exam (but has less complete metadata).
    best = candidates[0]
    for other in candidates[1:]:
        if top - other['score'] > 15:
            continue
        if all(norm(best[k]) == norm(other[k]) or
               not norm(best[k]) or not norm(other[k])
               for k in ('answer_session', 'answer_level', 'answer_part')):
            return 'version_review', None, 'Another plausible instruction version has incomplete metadata'
    return 'provisional', best, 'Metadata-only match; PDF not verified'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default='output/documents_preview.json')
    ap.add_argument('--out', default='output')
    args = ap.parse_args()
    docs = json.loads(Path(args.input).read_text(encoding='utf-8'))
    if not isinstance(docs, list):
        raise ValueError('Expected a JSON list of documents')
    tasks = [d for d in docs if d.get('document_type') == 'task']
    answers = [d for d in docs if d.get('document_type') == 'answer']
    by_key = defaultdict(list)
    for answer in answers:
        am, conflicts = meta(answer)
        if not conflicts and am['year'] is not None and am['subject']:
            by_key[(norm(am['year']), norm(am['subject']))].append((answer, am))
    rows = []
    for task in tasks:
        tm, conflicts = meta(task)
        candidates = []
        if not conflicts and tm['year'] is not None and tm['subject']:
            for answer, am in by_key[(norm(tm['year']), norm(tm['subject']))]:
                c = compare(tm, am, answer)
                if c is not None:
                    candidates.append(c)
        candidates.sort(key=lambda c: (-c['score'], c['answer_filename'] or ''))
        status, best, reason = decide(tm, candidates) if not conflicts else ('metadata_conflict', None, 'Task metadata contradict filename: ' + ', '.join(conflicts))
        rows.append({**{k: task.get(k) for k in FIELDS},
                     'task_filename': task.get('filename'),
                     'task_source_url': task.get('source_url'),
                     'match_status': status, 'review_reason': reason,
                     'answer_filename': best['answer_filename'] if best else None,
                     'answer_source_url': best['answer_source_url'] if best else None,
                     'best_score': candidates[0]['score'] if candidates else None,
                     'candidate_count': len(candidates), 'top_candidates': candidates[:10]})
    uses = Counter(r['answer_source_url'] for r in rows if r['answer_source_url'])
    for r in rows:
        if r['answer_source_url'] and uses[r['answer_source_url']] > 1:
            r['match_status'] = 'shared_answer_review'
            r['review_reason'] = 'Same answer PDF selected for multiple tasks'
    counts = Counter(r['match_status'] for r in rows)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'matches_v5.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = {'total_documents': len(docs), 'tasks': len(tasks), 'answers': len(answers),
               'status_counts': dict(counts), 'reused_answer_keys': sum(v > 1 for v in uses.values()),
               'notes': ['Metadata-only; PDFs not downloaded or verified.',
                         'Unknown task session requires review when answer session is explicit.',
                         'Multiple plausible versions require review; no automatic tie-break.']}
    (out / 'match_analysis_v5.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print('=== MATCH DOCUMENTS V5 ===')
    print('Tasks:', len(tasks), '| Answers:', len(answers))
    for status in ('no_candidate', 'provisional', 'ambiguous', 'session_review', 'version_review', 'shared_answer_review', 'metadata_conflict'):
        print(f'{status}: {counts[status]}')
    print('Saved:', out / 'matches_v5.json', 'and', out / 'match_analysis_v5.json')

if __name__ == '__main__':
    main()
