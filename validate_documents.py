
import json
from collections import Counter
from pathlib import Path

INPUT_FILE = Path("output/documents_preview.json")

with INPUT_FILE.open("r", encoding="utf-8") as f:
    documents = json.load(f)

print("=== DOCUMENT VALIDATION ===")
print("Total documents:", len(documents))

print("\n=== DOCUMENT TYPES ===")
for name, count in Counter(
    doc["document_type"] for doc in documents
).most_common():
    print(f"{name}: {count}")

print("\n=== ANSWERS BY YEAR ===")
answers = [
    doc for doc in documents
    if doc["document_type"] == "answer"
]

for year, count in sorted(
    Counter(doc.get("year") for doc in answers).items(),
    key=lambda item: (
        item[0] is None,
        -(item[0] or 0)
    )
):
    print(f"{year}: {count}")

print("\n=== ANSWERS WITHOUT SUBJECT ===")
missing_subject = [
    doc for doc in answers
    if not doc.get("subject")
]

print("Count:", len(missing_subject))

for doc in missing_subject[:15]:
    print(
        doc.get("year"),
        "|",
        doc["filename"]
    )

print("\n=== REVIEW DOCUMENTS ===")
reviews = [
    doc for doc in documents
    if doc["document_type"] == "review"
]

for doc in reviews[:30]:
    print(
        doc.get("year"),
        "|",
        doc.get("subject"),
        "|",
        doc["filename"]
    )

print("\nValidation completed!")
