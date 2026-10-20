
import requests
import re
import unicodedata

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote


# NSA website with VBE exam tasks
URL = (
    "https://www.nsa.smsm.lt/pasiekimu-departamentas/"
    "egzaminai-ir-pasiekimu-patikrinimai/"
    "valstybiniai-brandos-egzaminai/"
    "egzaminu-uzduotys/"
)


def normalize(text):
    """Normalize Lithuanian text for comparison."""

    text = text.lower()

    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )

    return re.sub(r"[-_\s.]+", " ", text)


def classify_document(header, filename):
    """Classify PDF using column header and filename."""

    header = normalize(header)
    filename = normalize(filename)

    # Exclude blank answer sheets
    if "atsakymu lapas" in header:
        return "excluded"

    if "atsakymu lapas" in filename:
        return "excluded"

    # Exclude auxiliary materials
    auxiliary_terms = [
        "formuliu",
        "formules",
        "priedas",
        "priedai",
        "atitiktis",
        "vertinimo instrukcija"
    ]

    if any(term in filename for term in auxiliary_terms):
        return "excluded"

    # Identify exam task columns
    if "vbe i dalis" in header:
        return "task"

    if "vbe ii dalis" in header:
        return "task"

    return "review"


def main():

    print("Connecting to NSA website...")

    try:
        response = requests.get(URL, timeout=30)
        response.raise_for_status()

    except requests.RequestException as error:
        print("Connection error:", error)
        return

    soup = BeautifulSoup(
        response.content,
        "html.parser"
    )

    tables = soup.find_all("table")

    print("Connection successful!")
    print("Total tables:", len(tables))

    # Inspect first 4 tables
    for table_number, table in enumerate(
        tables[:4], start=1
    ):

        print("\n" + "=" * 60)
        print("TABLE:", table_number)

        heading = table.find_previous("h4")

        if heading:
            print(
                "YEAR:",
                heading.get_text(" ", strip=True)
            )

        rows = table.find_all("tr")

        if not rows:
            continue

        # Read table column headers
        headers = [
            cell.get_text(" ", strip=True)
            for cell in rows[0].find_all(
                ["th", "td"],
                recursive=False
            )
        ]

        print("HEADERS:", headers)

        # Process first two data rows
        for row in rows[1:3]:

            cells = row.find_all(
                ["th", "td"],
                recursive=False
            )

            if not cells:
                continue

            subject = cells[0].get_text(
                " ", strip=True
            )

            print("\nSUBJECT:", subject)

            # Process document columns
            for column_index, cell in enumerate(
                cells[1:], start=1
            ):

                if column_index >= len(headers):
                    continue

                header = headers[column_index]

                # Find PDF links inside cell
                for link in cell.find_all(
                    "a", href=True
                ):

                    full_url = urljoin(
                        URL,
                        link["href"]
                    )

                    parsed_url = urlparse(full_url)

                    # Skip beta.etestavimas.lt
                    if (
                        parsed_url.hostname
                        == "beta.etestavimas.lt"
                    ):
                        continue

                    # Only process PDF files
                    if not parsed_url.path.lower().endswith(
                        ".pdf"
                    ):
                        continue

                    filename = unquote(
                        parsed_url.path
                    ).split("/")[-1]

                    # Classify document
                    document_type = classify_document(
                        header,
                        filename
                    )

                    print(
                        document_type.upper(),
                        "|",
                        header,
                        "|",
                        filename
                    )

    print("\nClassification test completed!")


if __name__ == "__main__":
    main()
