
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

tables = soup.find_all("table")

# Проверяем первые 4 таблицы
for table_number, table in enumerate(tables[:4], start=1):

    print(f"\n{'=' * 60}")
    print(f"TABLE {table_number}")

    heading = table.find_previous("h4")

    if heading:
        print("YEAR:", heading.get_text(" ", strip=True))

    rows = table.find_all("tr")

    for row_number, row in enumerate(rows[:3], start=1):

        print(f"\nROW {row_number}")

        cells = row.find_all(
            ["th", "td"],
            recursive=False
        )

        for column_number, cell in enumerate(cells):
            text = cell.get_text(" ", strip=True)

            print(
                f"Column {column_number}: {text[:100]}"
            )

            for link in cell.find_all("a", href=True):
                print("   LINK:", link.get("href"))
