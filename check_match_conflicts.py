
import json
from collections import defaultdict
from pathlib import Path

INPUT_FILE = Path("output/match_analysis.json")

with INPUT_FILE.open("r", encoding="utf-8") as f:
    matches = json.load(f)

answer_usage = defaultdict(list)

for item in matches:
    if item["status"] != "single_candidate":
        continue

    task = item["task"]
    answer = item["candidates"][0]

    answer_usage[answer["source_url"]].append(task)

conflicts = {
    url: tasks
    for url, tasks in answer_usage.items()
    if len(tasks) > 1
}

print("=== MATCH CONFLICT ANALYSIS ===")
print("Unique answers used:", len(answer_usage))
print("Answers used multiple times:", len(conflicts))

print("\n=== FIRST 10 CONFLICTS ===")

for index, (url, tasks) in enumerate(
    conflicts.items(), start=1
):
    if index > 10:
        break

    print("\nANSWER:", url.split("/")[-1])
    print("Matched tasks:", len(tasks))

    for task in tasks:
        print(" -", task["filename"])

OUTPUT_FILE = Path("output/match_conflicts.json")

OUTPUT_FILE.write_text(
    json.dumps(
        conflicts,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print("\nSaved:", OUTPUT_FILE)
