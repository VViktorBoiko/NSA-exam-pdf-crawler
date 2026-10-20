
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

SOURCES = {
    "VBE answers": (
        "https://www.nsa.smsm.lt/pasiekimu-departamentas/"
        "egzaminai-ir-pasiekimu-patikrinimai/"
        "valstybiniai-brandos-egzaminai/"
        "vertinimo-instrukcijos/"
    ),
    "PUPP answers": (
        "https://www.nsa.smsm.lt/pasiekimu-departamentas/"
        "egzaminai-ir-pasiekimu-patikrinimai/"
        "pagrindinio-ugdymo-pasiekimu-patikrinimai/"
        "pupp-vertinimo-instrukcijos/"
    )
}

for source_name, url in SOURCES.items():

    print("\n" + "=" * 70)
    print("SOURCE:", source_name)

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(
            response.content,
            "html.parser"
        )

        tables = soup.find_all("table")
        print("Total tables:", len(tables))

        pdf_count = 0

        for link in soup.find_all("a", href=True):
            full_url = urljoin(url, link["href"])

            if urlparse(full_url).path.lower().endswith(".pdf"):
                pdf_count += 1

        print("Total PDF links:", pdf_count)

        for table_number, table in enumerate(
            tables[:3], start=1
        ):
            print("\nTABLE:", table_number)

            heading = table.find_previous(
                ["h2", "h3", "h4"]
            )

            if heading:
                print(
                    "HEADING:",
                    heading.get_text(" ", strip=True)
                )

            rows = table.find_all("tr")

            for row in rows[:3]:
                print(
                    "ROW:",
                    row.get_text(" ", strip=True)[:200]
                )

                for link in row.find_all(
                    "a", href=True
                )[:3]:
                    print(
                        "LINK:",
                        urljoin(url, link["href"])
                    )

    except requests.RequestException as error:
        print("ERROR:", error)
