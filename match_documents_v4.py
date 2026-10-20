"""Conservative V4 metadata matcher (corrected VBE part capture) for NSA exam documents.
Run: python match_documents_v4.py --input output/documents_preview.json --out output
"""
import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

FIELDS = ('year', 'subject', 'exam_type', 'session', 'dalis', 'level')
WEIGHTS = {'year': 35, 'subject': 35, 'exam_type': 5, 'session': 15, 'dalis': 15, 'level': 10}

def normalized(value):
    s = unicodedata.normalize('NFKD', str(value or '')).lower()
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()

def part_from_filename(filename):
    s = normalized(filename)
    # Capture the part explicitly: VBE2, VBE_II, VBE-I, VBE 1.
    m = re.search(r'\bvbe\s*(ii|2|i|1)\b', s)
    if m:
        return 'II' if m.group(1) in ('ii', '2') else 'I'
    return None

def session_from_filename(filename):
    s = normalized(filename)
    # Avoid interpreting PG/PK inside other words.
    if re.search(r'\b(?:pk|pak|pakartotine|pakartotinis|pakartotines)\b', s):
        return 'pakartotinė'
    if re.search(r'\b(?:pg|pagr|pagrindine|pagrindinis|pagrindines)\b', s):
        return 'pagrindinė'
    return None

def metadata(doc):
    result = {key: doc.get(key) for key in FIELDS}
    part = part_from_filename(doc.get('filename'))
    session = session_from_filename(doc.get('filename'))
    conflicts = []
    if part:
        if result['dalis'] and result['dalis'] != part:
            conflicts.append('dalis')
        result['dalis'] = part
    if session:
        if result['session'] and normalized(result['session']) != normalized(session):
            conflicts.append('session')
        result['session'] = session
    return result, conflicts

def compare(task, answer):
    tm, tc = metadata(task)
    am, ac = metadata(answer)
    if tc or ac:
        return None
    matched, unknown = [], []
    for field in FIELDS:
        a, b = tm[field], am[field]
        if a is not None and b is not None:
            if normalized(a) != normalized(b):
                return None
            matched.append(field)
        else:
            unknown.append(field)
    # Year and subject must be known and equal.
    if not {'year', 'subject'}.issubset(matched):
        return None
    return {'answer_filename': answer.get('filename'),
            'answer_source_url': answer.get('source_url'),
            'score': sum(WEIGHTS[x] for x in matched),
            'matched_fields': matched, 'unknown_fields': unknown}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='output/documents_preview.json')
    parser.add_argument('--out', default='output')
    args = parser.parse_args()
    docs = json.loads(Path(args.input).read_text(encoding='utf-8'))
    tasks = [d for d in docs if d.get('document_type') == 'task']
    answers = [d for d in docs if d.get('document_type') == 'answer']
    by_key = defaultdict(list)
    for answer in answers:
        by_key[(answer.get('year'), normalized(answer.get('subject')))].append(answer)
    rows = []
    for task in tasks:
        candidates = [c for answer in by_key[(task.get('year'), normalized(task.get('subject')))]
                      if (c := compare(task, answer)) is not None]
        candidates.sort(key=lambda c: (-c['score'], c['answer_filename'] or ''))
        if not candidates:
            status = 'no_candidate'
        elif len(candidates) > 1 and candidates[0]['score'] - candidates[1]['score'] < 10:
            status = 'ambiguous'
        else:
            status = 'provisional'
        best = candidates[0] if status == 'provisional' else None
        rows.append({**{key: task.get(key) for key in ('year', 'subject', 'exam_type', 'session', 'srautas', 'dalis', 'level')},
                     'task_filename': task.get('filename'), 'task_source_url': task.get('source_url'),
                     'match_status': status, 'answer_filename': best['answer_filename'] if best else None,
                     'answer_source_url': best['answer_source_url'] if best else None,
                     'best_score': candidates[0]['score'] if candidates else None,
                     'candidate_count': len(candidates), 'top_candidates': candidates[:5]})
    # Shared-answer matches are flagged for review, not assumed invalid.
    uses = Counter(r['answer_source_url'] for r in rows if r['answer_source_url'])
    for r in rows:
        if r['answer_source_url'] and uses[r['answer_source_url']] > 1:
            r['match_status'] = 'shared_answer_review'
    counts = Counter(r['match_status'] for r in rows)
    summary = {'total_documents': len(docs), 'tasks': len(tasks), 'answers': len(answers),
               'status_counts': dict(counts),
               'reused_answer_keys': sum(v > 1 for v in uses.values()),
               'notes': ['Metadata-only matches; PDF content not verified.',
                         'Explicit filename part/session conflicts reject candidates.',
                         'Unknown fields never count as matches.']}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'matches_v4.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / 'match_analysis_v4.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print('=== MATCH DOCUMENTS V4 ===')
    print('Tasks:', len(tasks), '| Answers:', len(answers))
    for key in ('no_candidate', 'ambiguous', 'provisional', 'shared_answer_review'):
        print(f'{key}: {counts[key]}')
    print('Saved:', out / 'matches_v4.json', 'and', out / 'match_analysis_v4.json')

if __name__ == '__main__':
    main()
