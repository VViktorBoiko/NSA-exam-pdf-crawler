
import json
from pathlib import Path

INPUT_FILE = Path("output/match_analysis.json")
OUTPUT_FILE = Path("output/match_details.txt")

with INPUT_FILE.open("r", encoding="utf-8") as f:
    matches = json.load(f)

fields = [
    "year",
    "subject",
    "exam_type",
    "session",
    "srautas",
    "dalis",
    "level",
]

lines = []
shown = 0

for item in matches:
    if item["status"] != "single_candidate":
        continue

    task = item["task"]
    answer = item["candidates"][0]

    lines.append("=" * 70)
    lines.append(f"TASK: {task['filename']}")
    lines.append(f"ANSWER: {answer['filename']}")
    lines.append("")

    for field in fields:
        task_value = task.get(field)
        answer_value = answer.get(field)

        if task_value is None or answer_value is None:
            status = "UNKNOWN"
        elif task_value == answer_value:
            status = "MATCH"
        else:
            status = "CONFLICT"

        lines.append(
            f"{field}: "
            f"TASK={task_value} | "
            f"ANSWER={answer_value} | "
            f"{status}"
        )

    lines.append("")
    shown += 1

    if shown >= 20:
        break

report = "\n".join(lines)

OUTPUT_FILE.write_text(report, encoding="utf-8")

print(report)
print(f"\nSaved: {OUTPUT_FILE}")
