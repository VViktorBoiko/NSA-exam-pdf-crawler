
import requests
from bs4 import BeautifulSoup

URL = (
    "https://www.nsa.smsm.lt/pasiekimu-departamentas/"
    "egzaminai-ir-pasiekimu-patikrinimai/"
    "valstybiniai-brandos-egzaminai/"
    "egzaminu-uzduotys/"
)

response = requests.get(URL, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.content, "html.parser")

print("=== PAGE HEADINGS ===")

for heading in soup.find_all(
    ["h1", "h2", "h3", "h4", "h5", "h6"]
):
    text = heading.get_text(" ", strip=True)

    if text:
        print(heading.name, ":", text[:150])

print("\n=== FIRST 5 TABLES ===")

tables = soup.find_all("table")

print("Total tables:", len(tables))

for index, table in enumerate(tables[:5], start=1):
    print("\nTABLE", index)

    previous_heading = table.find_previous(
        ["h1", "h2", "h3", "h4", "h5", "h6"]
    )

    if previous_heading:
        print(
            "Previous heading:",
            previous_heading.get_text(" ", strip=True)
        )

    rows = table.find_all("tr")

    for row in rows[:3]:
        print("ROW:", row.get_text(" ", strip=True)[:250])
