
import json
import random
from collections import Counter

with open("output/final_dataset.json", encoding="utf-8") as f:
    data = json.load(f)

print("Total:", len(data))
print("Statuses:", dict(Counter(x["status"] for x in data)))

random.seed(42)

groups = [
    ("found", [x for x in data if x["status"] == "found"], 15),
    ("missing_no_candidate", [
        x for x in data
        if x["status"] == "missing"
        and x["match_status"] == "no_candidate"
    ], 10),
    ("needs_review", [
        x for x in data
        if x["status"] == "missing"
        and x.get("review_required")
    ], 15),
    ("broken_link", [
        x for x in data if x["status"] == "broken_link"
    ], 10),
]

for group_name, records, count in groups:
    print(f"\n=== {group_name.upper()} ===")
    for x in random.sample(records, min(count, len(records))):
        print(f"\nID: {x['id']}")
        print("Year:", x["year"])
        print("Subject:", x["subject"])
        print("Task:", x["task_filename"])
        print("Answer:", x["answer_filename"])
        print("Status:", x["status"])
        print("Reason:", x["status_reason"])
        print("Task path:", x["task"]["local_path"])
        print("Answer path:", x["answer"]["local_path"])
        print("Candidates:", x["candidate_count"])
        for candidate in x["top_candidates"][:3]:
            print("  -", candidate["answer_filename"])
