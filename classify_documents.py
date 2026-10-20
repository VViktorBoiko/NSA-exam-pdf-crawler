
import json
import re
from collections import Counter
from urllib.parse import urlparse, unquote
from pathlib import Path

INPUT_FILE = Path("pdf_links_preview.json")
OUTPUT_FILE = Path("classified_preview.json")


def classify_document(document):
    source = document["source"]

    filename = unquote(
        urlparse(document["url"]).path
    ).split("/")[-1].lower()

    normalized = re.sub(
        r"[-_\s]+", " ", filename
    )

    # Blank answer sheets are NOT answer keys
    if (
        "atsakymu lapas" in normalized
        or "atsakymų lapas" in normalized
        or "ats lapas" in normalized
    ):
        return "excluded"

    # Auxiliary documents
    if any(term in normalized for term in [
        "formules",
        "formulės",
        "priedas",
        "priedai",
        "instrukcija mokiniui"
    ]):
        return "excluded"

    # Answer-key source pages
    if source.endswith("_answers"):
        return "answer"

    # Explicit task markers
    if any(term in normalized for term in [
        "uzduotis",
        "užduotis",
        "uzduotys",
        "užduotys"
    ]):
        return "task"

    # Unknown documents require review
    return "review"


with INPUT_FILE.open(
    "r", encoding="utf-8"
) as file:
    documents = json.load(file)

for document in documents:
    document["document_type"] = classify_document(
        document
    )

counts = Counter(
    document["document_type"]
    for document in documents
)

print("=== DOCUMENT CLASSIFICATION ===")

for document_type in [
    "task", "answer", "excluded", "review"
]:
    print(
        f"{document_type}: "
        f"{counts[document_type]}"
    )

with OUTPUT_FILE.open(
    "w", encoding="utf-8"
) as file:
    json.dump(
        documents,
        file,
        ensure_ascii=False,
        indent=4
    )

print("\nSaved to:", OUTPUT_FILE)

print("\n=== FIRST 10 REVIEW FILES ===")

review_files = [
    doc for doc in documents
    if doc["document_type"] == "review"
]

for document in review_files[:10]:
    print(
        document["source"],
        "|",
        document["filename"]
    )
