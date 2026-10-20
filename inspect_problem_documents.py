
import json
from pathlib import Path
from collections import Counter

INPUT = Path("output/documents_preview.json")
OUTPUT = Path("output/problem_documents.txt")

with INPUT.open("r", encoding="utf-8") as f:
    documents = json.load(f)

problem_documents = []

for doc in documents:
    doc_type = doc.get("document_type")
    filename = doc.get("filename", "")
    subject = doc.get("subject")

    if doc_type == "review":
        reason = "Needs classification"

    elif doc_type == "answer" and not subject:
        reason = "Answer without subject"

    else:
        continue

    problem_documents.append({
        "reason": reason,
        "document": doc
    })

lines = []

for item in problem_documents:
    doc = item["document"]

    lines.append("=" * 65)
    lines.append("REASON: " + item["reason"])
    lines.append("FILE: " + str(doc.get("filename")))
    lines.append("YEAR: " + str(doc.get("year")))
    lines.append("SUBJECT: " + str(doc.get("subject")))
    lines.append("SOURCE: " + str(doc.get("source")))
    lines.append("LINK TEXT: " + str(doc.get("link_text")))
    lines.append("URL: " + str(doc.get("source_url")))
    lines.append("")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(lines), encoding="utf-8")

print("=== PROBLEM DOCUMENT ANALYSIS ===")
print("Total:", len(problem_documents))

counts = Counter(
    item["reason"] for item in problem_documents
)

for reason, count in counts.items():
    print(f"{reason}: {count}")

print("\nSaved:", OUTPUT)
