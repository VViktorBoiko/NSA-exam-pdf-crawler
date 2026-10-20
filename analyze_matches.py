
import json
from collections import Counter, defaultdict
from pathlib import Path

INPUT_FILE = Path("output/documents_preview.json")
OUTPUT_FILE = Path("output/match_analysis.json")

with INPUT_FILE.open("r", encoding="utf-8") as f:
    documents = json.load(f)

tasks = [
    doc for doc in documents
    if doc["document_type"] == "task"
]

answers = [
    doc for doc in documents
    if doc["document_type"] == "answer"
]


def compatible(task, answer):
    """Check whether two documents can belong together."""

    # VBE and PUPP must not be mixed
    task_family = task["source"].split("_")[0]
    answer_family = answer["source"].split("_")[0]

    if task_family != answer_family:
        return False

    # Require exact year, subject and exam type
    for field in ("year", "subject", "exam_type"):
        if task.get(field) != answer.get(field):
            return False

    # Reject known conflicts
    for field in ("session", "srautas", "dalis", "level"):
        task_value = task.get(field)
        answer_value = answer.get(field)

        if (
            task_value is not None
            and answer_value is not None
            and task_value != answer_value
        ):
            return False

    return True


results = []
counts = Counter()
answer_usage = defaultdict(list)

for task in tasks:
    candidates = [
        answer for answer in answers
        if compatible(task, answer)
    ]

    if len(candidates) == 0:
        status = "no_candidate"
    elif len(candidates) == 1:
        status = "single_candidate"
        answer_usage[candidates[0]["source_url"]].append(
            task["filename"]
        )
    else:
        status = "multiple_candidates"

    counts[status] += 1

    results.append({
        "task": task,
        "status": status,
        "candidate_count": len(candidates),
        "candidates": candidates
    })

OUTPUT_FILE.parent.mkdir(
    parents=True, exist_ok=True
)

with OUTPUT_FILE.open("w", encoding="utf-8") as f:
    json.dump(
        results,
        f,
        ensure_ascii=False,
        indent=2
    )

conflicts = {
    url: filenames
    for url, filenames in answer_usage.items()
    if len(filenames) > 1
}

print("=== IMPROVED MATCH ANALYSIS ===")
print("Tasks:", len(tasks))
print("Answers:", len(answers))
print("No candidate:", counts["no_candidate"])
print("Single candidate:", counts["single_candidate"])
print("Multiple candidates:", counts["multiple_candidates"])
print("Answers reused:", len(conflicts))

print("\n=== FIRST 5 SINGLE CANDIDATES ===")

shown = 0

for item in results:
    if item["status"] != "single_candidate":
        continue

    task = item["task"]
    answer = item["candidates"][0]

    print("\nTASK:", task["filename"])
    print("ANSWER:", answer["filename"])

    shown += 1
    if shown >= 5:
        break

print("\nSaved:", OUTPUT_FILE)
