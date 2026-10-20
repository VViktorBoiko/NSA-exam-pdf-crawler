
import json
from pathlib import Path
from collections import Counter

path = Path("output/documents_preview.json")

with path.open("r", encoding="utf-8") as f:
    documents = json.load(f)

reviews = [
    doc for doc in documents
    if doc.get("document_type") == "review"
]

categories = Counter()

for doc in reviews:
    text = (
        doc.get("filename", "") + " " +
        doc.get("link_text", "")
    ).lower()

    if any(term in text for term in [
        "mokym", "medziaga", "medžiaga",
        "seminar", "skaidres"
    ]):
        category = "training_material"

    elif any(term in text for term in [
        "vertinimo-instrukcija",
        "vertinimo_instrukcija",
        "vertinimo instrukcija",
        "vert_instr"
    ]):
        category = "possible_answer"

    else:
        category = "unknown"

    categories[category] += 1

    doc["review_category"] = category

print("=== REVIEW ANALYSIS ===")
print("Total review:", len(reviews))

for category, count in categories.items():
    print(f"{category}: {count}")

print("\n=== POSSIBLE ANSWERS ===")

for doc in reviews:
    if doc["review_category"] == "possible_answer":
        print(doc["filename"])

output = Path("output/review_analysis.json")

with output.open("w", encoding="utf-8") as f:
    json.dump(reviews, f, ensure_ascii=False, indent=2)

print("\nSaved:", output)
