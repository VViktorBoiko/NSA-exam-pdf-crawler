"""Diagnose V3 matching gaps without modifying crawler data.
Run: python diagnose_matching.py --input output/documents_preview.json --matches output/matches_v3.json --out output
"""
import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


def norm(value):
    value = unicodedata.normalize('NFKD', str(value or '')).lower()
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def session(doc):
    name = norm(doc.get('filename'))
    if re.search(r'\b(pk|pak|pakart\w*)\b', name):
        return 'repeat'
    if re.search(r'\b(pg|pagr\w*)\b', name):
        return 'main'
    value = norm(doc.get('session'))
    if value.startswith('pakart'): return 'repeat'
    if value.startswith('pagr'): return 'main'
    return None


def part(doc):
    name = norm(doc.get('filename'))
    m = re.search(r'\bvbe\s*(ii|2|i|1)\b', name)
    if m: return 'II' if m.group(1) in ('ii', '2') else 'I'
    return doc.get('dalis')


def reason(task, answers, reviews):
    y, s = task.get('year'), norm(task.get('subject'))
    same_subject = [a for a in answers if norm(a.get('subject')) == s and s]
    same_year = [a for a in same_subject if a.get('year') == y]
    if not same_year:
        possible_reviews = [r for r in reviews if r.get('year') == y and norm(r.get('subject')) == s]
        if possible_reviews: return 'potential_answer_in_review', possible_reviews
        missing_year = [a for a in same_subject if a.get('year') is None]
        if missing_year: return 'answer_year_missing', missing_year
        return ('no_answer_same_subject' if not same_subject else 'no_answer_same_year'), same_subject[:5]
    compatible_exam = [a for a in same_year if not (task.get('exam_type') and a.get('exam_type') and norm(task['exam_type']) != norm(a['exam_type']))]
    if not compatible_exam: return 'exam_type_conflict', same_year
    compatible_session = [a for a in compatible_exam if not (session(task) and session(a) and session(task) != session(a))]
    if not compatible_session: return 'session_conflict', compatible_exam
    compatible_part = [a for a in compatible_session if not (part(task) and part(a) and part(task) != part(a))]
    if not compatible_part: return 'part_conflict', compatible_session
    compatible_level = [a for a in compatible_part if not (task.get('level') and a.get('level') and norm(task['level']) != norm(a['level']))]
    if not compatible_level: return 'level_conflict', compatible_part
    return 'other_metadata_or_internal_conflict', compatible_level


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default='output/documents_preview.json')
    ap.add_argument('--matches', default='output/matches_v3.json')
    ap.add_argument('--out', default='output')
    args = ap.parse_args()
    docs = json.loads(Path(args.input).read_text(encoding='utf-8'))
    matches = json.loads(Path(args.matches).read_text(encoding='utf-8'))
    answers = [d for d in docs if d.get('document_type') == 'answer']
    reviews = [d for d in docs if d.get('document_type') == 'review']
    tasks = {d.get('source_url'): d for d in docs if d.get('document_type') == 'task'}
    report, counts = [], Counter()
    for row in matches:
        if row.get('match_status') != 'no_candidate': continue
        task = tasks.get(row.get('task_source_url'))
        if task is None:
            why, related = 'task_not_found_by_url', []
        else:
            why, related = reason(task, answers, reviews)
        counts[why] += 1
        report.append({'task_filename': row.get('task_filename'), 'task_source_url': row.get('task_source_url'),
                       'year': row.get('year'), 'subject': row.get('subject'), 'reason': why,
                       'related_documents': [{'filename': x.get('filename'), 'document_type': x.get('document_type'),
                                              'year': x.get('year'), 'session': x.get('session'),
                                              'dalis': x.get('dalis'), 'level': x.get('level')} for x in related[:8]]})
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / 'matching_diagnostics.json').write_text(json.dumps({'counts': dict(counts), 'cases': report}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('=== V3 DIAGNOSTICS ===')
    print('No-candidate tasks:', len(report))
    for key, count in counts.most_common(): print(f'{key}: {count}')
    print('Saved:', out / 'matching_diagnostics.json')
    print('Note: heuristic explanations, not verified PDF matches.')

if __name__ == '__main__': main()
