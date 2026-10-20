"""Conservative metadata-based matching for NSA VBE/PUPP exam PDFs.

Run from the project root: python match_documents_v2.py
Reads output/documents_preview.json; writes output/matches_v2.json and
output/match_analysis_v2.json. No PDFs are downloaded or modified.
"""
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

INPUT = Path('output/documents_preview.json')
OUTPUT = Path('output/matches_v2.json')
REPORT = Path('output/match_analysis_v2.json')


def normalized(value):
    if value is None:
        return ''
    text = unicodedata.normalize('NFKD', str(value)).casefold()
    return ''.join(c for c in text if not unicodedata.combining(c)).strip()


def exam_family(doc):
    source = doc.get('source') or ''
    if source.startswith('VBE_'):
        return 'VBE'
    if source.startswith('PUPP_'):
        return 'PUPP'
    return None


def normalized_subject(value):
    text = normalized(value)
    return re.sub(r'\s+', ' ', text)


def value(doc, field):
    return normalized(doc.get(field))


def compatible(task, answer):
    """Reject explicit contradictions; never treat missing fields as proof."""
    if exam_family(task) != exam_family(answer):
        return False
    for field in ('year', 'subject', 'exam_type', 'session', 'srautas', 'dalis', 'level'):
        a, b = value(task, field), value(answer, field)
        if a and b and a != b:
            return False
    return True


def score_match(task, answer):
    weights = {'year': 25, 'subject': 35, 'exam_type': 8,
               'session': 12, 'srautas': 8, 'dalis': 12, 'level': 10}
    score = 0
    evidence = []
    unknown = []
    for field, weight in weights.items():
        a, b = value(task, field), value(answer, field)
        if a and b:
            score += weight
            evidence.append(field)
        else:
            unknown.append(field)
    return score, evidence, unknown


def main():
    if not INPUT.exists():
        raise SystemExit(f'Input not found: {INPUT}. Run main_crawler_updated.py first.')
    with INPUT.open(encoding='utf-8') as handle:
        docs = json.load(handle)
    if not isinstance(docs, list):
        raise SystemExit('Expected a JSON array of documents.')

    tasks = [d for d in docs if d.get('document_type') == 'task']
    answers = [d for d in docs if d.get('document_type') == 'answer']
    # Only actual answer keys; mock/sample/review excluded on purpose.
    answer_by_group = defaultdict(list)
    for a in answers:
        answer_by_group[(exam_family(a), value(a, 'year'))].append(a)

    matches = []
    used_by = defaultdict(list)
    for task in tasks:
        year = value(task, 'year')
        # A missing year must not match across years indiscriminately.
        pool = answer_by_group.get((exam_family(task), year), []) if year else []
        candidates = []
        for answer in pool:
            if not compatible(task, answer):
                continue
            score, evidence, unknown = score_match(task, answer)
            # Both year and subject must be explicitly present and equal.
            if 'year' not in evidence or 'subject' not in evidence:
                continue
            candidates.append({'answer_filename': answer.get('filename'),
                               'answer_source_url': answer.get('source_url'),
                               'score': score, 'matched_fields': evidence,
                               'unknown_fields': unknown})
        candidates.sort(key=lambda x: (-x['score'], x['answer_filename'] or ''))
        top = candidates[0]['score'] if candidates else None
        best = [c for c in candidates if c['score'] == top] if candidates else []
        # If two equally good matches exist, do not guess.
        if not candidates:
            status = 'no_candidate'
        elif len(best) > 1:
            status = 'ambiguous'
        elif top < 68:
            status = 'low_confidence'
        else:
            status = 'provisional'
        selected = best[0] if status == 'provisional' else None
        if selected:
            used_by[selected['answer_source_url']].append(task.get('source_url'))
        matches.append({
            'task_filename': task.get('filename'),
            'task_source_url': task.get('source_url'),
            'year': task.get('year'), 'subject': task.get('subject'),
            'exam_type': task.get('exam_type'), 'session': task.get('session'),
            'srautas': task.get('srautas'), 'dalis': task.get('dalis'),
            'level': task.get('level'), 'family': exam_family(task),
            'match_status': status,
            'answer_source_url': selected['answer_source_url'] if selected else None,
            'answer_filename': selected['answer_filename'] if selected else None,
            'best_score': top, 'candidate_count': len(candidates),
            'top_candidates': candidates[:5],
        })

    # Shared keys can legitimately cover multiple task parts, but require review.
    reused = {url: tasks for url, tasks in used_by.items() if len(tasks) > 1}
    for m in matches:
        if m['answer_source_url'] in reused:
            m['match_status'] = 'shared_answer_review'

    counts = Counter(m['match_status'] for m in matches)
    report = {
        'total_documents': len(docs), 'tasks': len(tasks), 'answers': len(answers),
        'status_counts': dict(sorted(counts.items())),
        'reused_answer_keys': len(reused),
        'tasks_missing_year': sum(not d.get('year') for d in tasks),
        'tasks_missing_subject': sum(not d.get('subject') for d in tasks),
        'notes': [
            'All matches are metadata-based and provisional, not verified against PDF content.',
            'Missing metadata is not treated as equality; year and subject are required.',
            'This is a diagnostic matching report, not the final assignment index.',
            'Multiple task PDFs can legitimately share one answer key; such cases require review.',
        ],
        'examples': {status: [m['task_filename'] for m in matches
                              if m['match_status'] == status][:10]
                     for status in sorted(counts)},
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(matches, ensure_ascii=False, indent=2), encoding='utf-8')
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('=== MATCH DOCUMENTS V2 ===')
    print('Tasks:', len(tasks), '| Answers:', len(answers))
    for status, count in sorted(counts.items()):
        print(f'{status}: {count}')
    print('Answer keys linked to multiple tasks:', len(reused))
    print('Saved:', OUTPUT, 'and', REPORT)


if __name__ == '__main__':
    main()
