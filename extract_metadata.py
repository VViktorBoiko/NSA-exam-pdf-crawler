
import requests
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote

URL = (
    "https://www.nsa.smsm.lt/pasiekimu-departamentas/"
    "egzaminai-ir-pasiekimu-patikrinimai/"
    "valstybiniai-brandos-egzaminai/"
    "egzaminu-uzduotys/"
)

response = requests.get(URL, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.content, "html.parser")

records = []

for table in soup.find_all("table"):

    heading = table.find_previous("h4")
    if not heading:
        continue

    year_text = heading.get_text(" ", strip=True)

    if not re.fullmatch(r"20\d{2}", year_text):
        continue

    year = int(year_text)

    rows = table.find_all("tr")

    for row in rows[1:]:

        cells = row.find_all(["td", "th"], recursive=False)

        if len(cells) < 2:
            continue

        subject_text = cells[0].get_text(" ", strip=True)

        level = None

        if "Bendrasis kursas" in subject_text:
            level = "bendrasis"
        elif "Išplėstinis kursas" in subject_text:
            level = "išplėstinis"

        subject = re.sub(
            r"\s*\([^)]*kursas\)",
            "",
            subject_text,
            flags=re.IGNORECASE
        ).strip()

        for cell in cells[1:]:
            for link in cell.find_all("a", href=True):

                pdf_url = urljoin(URL, link["href"])
                filename = unquote(
                    urlparse(pdf_url).path
                ).split("/")[-1]

                lower_name = filename.lower()

                if not lower_name.endswith(".pdf"):
                    continue

                if "beta.etestavimas.lt" in urlparse(pdf_url).netloc.lower():
                    continue

                if (
                    "atsakymu-lapas" in lower_name
                    or "atsakymų-lapas" in lower_name
                    or "formules" in lower_name
                ):
                    continue

                records.append({
                    "year": year,
                    "subject": subject,
                    "exam_type": "valstybinis",
                    "session": None,
                    "srautas": None,
                    "dalis": None,
                    "level": level,
                    "source_url": pdf_url
                })

print("Metadata records extracted:", len(records))

print("\nFirst 5 records:\n")

for record in records[:5]:
    print(json.dumps(record, ensure_ascii=False, indent=4))

with open("metadata_preview.json", "w", encoding="utf-8") as file:
    json.dump(records, file, ensure_ascii=False, indent=4)

print("\nSaved to metadata_preview.json")
