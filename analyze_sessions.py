
import json
from collections import Counter

INPUT_FILE = "output/documents_preview.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    documents = json.load(f)

missing = [
    doc for doc in documents
    if doc.get("session") is None
]

print("=== SESSION ANALYSIS ===")
print(f"Total documents: {len(documents)}")
print(f"Missing session: {len(missing)}")

print("\n=== BY SOURCE ===")
for source, count in Counter(
    doc["source"] for doc in missing
).most_common():
    print(f"{source}: {count}")

print("\n=== BY YEAR ===")
for year, count in sorted(
    Counter(
        doc["year"] for doc in missing
    ).items(),
    reverse=True
):
    print(f"{year}: {count}")

print("\n=== FIRST 30 MISSING SESSIONS ===")
for doc in missing[:30]:
    print(
        f"{doc['year']} | "
        f"{doc['source']} | "
        f"{doc['filename']}"
    )

with open(
    "output/missing_sessions.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        missing,
        f,
        ensure_ascii=False,
        indent=4
    )

print("\nSaved: output/missing_sessions.json")
