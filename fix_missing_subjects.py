
import json
import re
from collections import Counter
from pathlib import Path

INPUT = Path("output/documents_preview.json")
OUTPUT = Path("output/subjects_fixed_preview.json")

SUBJECT_CODES = {
    "BIO": "Biologija",
    "MAT": "Matematika",
    "IST": "Istorija",
    "FIZ": "Fizika",
    "CH": "Chemija",
    "CHE": "Chemija",
    "GEO": "Geografija",
    "IT": "Informatika",
    "LKL": "Lietuvių kalba ir literatūra",
    "EN": "Užsienio kalba (anglų)",
    "FR": "Užsienio kalba (prancūzų)",
    "DE": "Užsienio kalba (vokiečių)",
    "RU": "Užsienio kalba (rusų)",
    "PL": "Gimtoji kalba (lenkų)",
    "BL": "Gimtoji kalba (baltarusių)",
}

def detect_subject(filename):
    name = filename.upper()

    # Handle codes joined to years or words,
    # e.g. 2023BIOPagrvertinimo...
    for code, subject in SUBJECT_CODES.items():
        pattern = (
            r"(?<![A-Z])"
            + re.escape(code)
            + r"(?=[^A-Z]|PAGR|PAKART|VERT|RAS)"
        )

        if re.search(pattern, name):
            return subject

    return None


with INPUT.open("r", encoding="utf-8") as f:
    documents = json.load(f)

fixed = Counter()

for doc in documents:
    if doc.get("subject"):
        continue

    subject = detect_subject(doc.get("filename", ""))

    if subject:
        doc["subject"] = subject
        fixed[subject] += 1

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", encoding="utf-8") as f:
    json.dump(
        documents,
        f,
        ensure_ascii=False,
        indent=2
    )

print("=== SUBJECT RECOVERY ===")
print("Total documents:", len(documents))
print("Subjects recovered:", sum(fixed.values()))

for subject, count in fixed.most_common():
    print(f"{subject}: {count}")

print("\nRemaining without subject:",
      sum(not doc.get("subject") for doc in documents))

print("\nSaved:", OUTPUT)
