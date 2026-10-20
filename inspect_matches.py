
import json
from collections import Counter
from pathlib import Path

input_path = Path("output/match_analysis.json")

with input_path.open("r", encoding="utf-8") as f:
    matches = json.load(f)

fields = [
    "year",
    "subject",
    "session",
    "dalis",
    "level"
]

statistics = Counter()

print("=== MATCH QUALITY ANALYSIS ===")

for item in matches:
    if item["status"] != "single_candidate":
        continue

    task = item["task"]
    answer = item["candidates"][0]

    missing = []

    for field in fields:
        if task.get(field) is None or answer.get(field) is None:
            missing.append(field)
            statistics[field] += 1

    if not missing:
        statistics["complete"] += 1

print("\n=== STATISTICS ===")

print("Complete metadata:", statistics["complete"])

for field in fields:
    print(f"Missing {field}: {statistics[field]}")

print("\n=== FIRST 10 INCOMPLETE MATCHES ===")

shown = 0

for item in matches:
    if item["status"] != "single_candidate":
        continue

    task = item["task"]
    answer = item["candidates"][0]

    missing = [
        field for field in fields
        if task.get(field) is None
        or answer.get(field) is None
    ]

    if not missing:
        continue

    print("\nTASK:", task["filename"])
    print("ANSWER:", answer["filename"])
    print("Missing fields:", ", ".join(missing))

    shown += 1

    if shown >= 10:
        break

print("\nAnalysis completed!")
