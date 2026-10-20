
from fileinput import filename
import json
import logging
import re
import unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup


BASE_URL = (
    "https://www.nsa.smsm.lt/pasiekimu-departamentas/"
    "egzaminai-ir-pasiekimu-patikrinimai/"
)

SOURCES = {
    "VBE_tasks": (
        BASE_URL
        + "valstybiniai-brandos-egzaminai/egzaminu-uzduotys/"
    ),
    "VBE_answers": (
        BASE_URL
        + "valstybiniai-brandos-egzaminai/vertinimo-instrukcijos/"
    ),
    "PUPP_tasks": (
        BASE_URL
        + "pagrindinio-ugdymo-pasiekimu-patikrinimai/pupp-uzduotys/"
    ),
    "PUPP_answers": (
        BASE_URL
        + "pagrindinio-ugdymo-pasiekimu-patikrinimai/"
        "pupp-vertinimo-instrukcijos/"
    ),
}

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename="crawler.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)


def normalize(text):
    """Normalize Lithuanian text."""
    text = text.lower()

    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )

    return re.sub(r"[-_\s.]+", " ", text).strip()


def fetch_page(url):
    """Fetch an NSA page."""
    try:
        response = requests.get(url, timeout=40)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")

    except requests.RequestException as error:
        logging.error("Page error: %s - %s", url, error)
        print("ERROR:", url, error)
        return None


def extract_year(table):
    """Find the closest preceding year heading."""
    for heading in table.find_all_previous(
        ["h2", "h3", "h4", "h5"]
    ):
        value = heading.get_text(" ", strip=True)
        match = re.fullmatch(r"(20\d{2})\s*m?\.?", value)

        if match:
            return int(match.group(1))

    return None


def extract_year_from_filename(filename, source_url=""):
    match = re.search(
        r"(?<!\d)(20\d{2})(?!\d)",
        filename
    )

    if match:
        return int(match.group(1))

    match = re.search(
        r"/(?:wp-content/uploads/)(20\d{2})/",
        source_url
    )

    if match:
        return int(match.group(1))

    return None


def extract_session_from_filename(filename):
    name = normalize(filename)

    repeat_patterns = [
        r"pakartotin",
        r"(?<![a-z])pak(?![a-z])",
        r"(?<![a-z])pk\d*(?![a-z])",
    ]

    main_patterns = [
        r"pagrindin",
        r"(?<![a-z])pagr(?![a-z])",
        r"(?<![a-z])pg\d*(?![a-z])",
    ]

    if any(re.search(p, name) for p in repeat_patterns):
        return "pakartotinė"

    if any(re.search(p, name) for p in main_patterns):
        return "pagrindinė"

    return None


def extract_subject(text):
    """Extract subject and level from a table row."""
    original = " ".join(text.split())
    normalized = normalize(original)

    level = None

    if "bendrasis kursas" in normalized:
        level = "bendrasis"
    elif "isplestinis kursas" in normalized:
        level = "išplėstinis"

    subject = re.split(
        r"(?=\b20\d{2}\s*m\.)",
        original,
        maxsplit=1
    )[0].strip()

    subject = re.sub(
        r"\s*\((?:Bendrasis|Išplėstinis)\s+kursas\)",
        "",
        subject,
        flags=re.IGNORECASE
    ).strip()

    return subject, level

def extract_exam_type(source_name, filename):
    name = filename.upper()

    if "PUPP" in source_name.upper():
        return "PUPP"

    if re.search(r"(?<![A-Z])MBE(?![A-Z])", name):
        return "mokyklinis"

    if source_name.startswith("VBE"):
        return "valstybinis"

    return None

def extract_session(filename, context=""):
    """Detect exam session from explicit markers."""
    name = normalize(filename)
    context = normalize(context)

    if (
        "pakartotine" in name
        or "pakart" in name
        or re.search(r"\bpk\b", name)
    ):
        return "pakartotinė"

    if (
        "pagrindine" in name
        or "pagr" in name
        or re.search(r"\bpg\b", name)
    ):
        return "pagrindinė"

    if "pakartotine" in context:
        return "pakartotinė"

    if "pagrindine" in context:
        return "pagrindinė"

    return None


def extract_part(header, filename):
    """Identify exam part."""
    text = normalize(header)

    if "ii dalis" in text or "ii dalies" in text:
        return "II"

    if "i dalis" in text:
        return "I"

    name = normalize(filename)

    if re.search(r"\bvbe ii\b", name):
        return "II"

    if re.search(r"\bvbe i\b", name):
        return "I"

    return None


def classify_document(source, header, filename):
    """Classify exam PDFs using source and filename."""

    header = normalize(header)
    name = normalize(filename)

    # Identify sample documents (pvz = pavyzdys)
    is_sample = bool(
        re.search(r"\bpvz\b", name)
        or "pavyzd" in name
    )

    # Identify evaluation documents
    evaluation_terms = [
        "vertinimo instrukcija",
        "vertinimo instrukcijos",
        "vert instr",
        "vertinimas",
        "vertinimo",
    ]

    is_evaluation = (
        any(term in name for term in evaluation_terms)
        or bool(re.search(r"\bvert\b", name))
    )

    # Exclude blank answer sheets and auxiliary files
    excluded_terms = [
        "atsakymu lapas",
        "atsakymu lapai",
        "formuliu",
        "formules",
        "formulynas",
        "priedas",
        "priedai",
        "atitiktis",
    ]

    if "atsakymu lapas" in header:
        return "excluded"

    if any(term in name for term in excluded_terms):
        return "excluded"

    # Separate sample tasks and sample evaluations
    if is_sample:
        if is_evaluation or source.endswith("_answers"):
            return "sample_answer"
        return "sample_task"

    # Evaluation instructions found on task pages
    if is_evaluation:
        return "answer"

    # Documents on answer pages
    if source.endswith("_answers"):
        return "answer"

    # Documents on task pages
    if source.endswith("_tasks"):
        return "task"

    return "review"


def collect_documents(source_name, soup):
    """Collect structured PDF candidates from tables."""
    documents = []
    source_url = SOURCES[source_name]
    seen = set()

    for table in soup.find_all("table"):
        year = extract_year(table)
        rows = table.find_all("tr")

        if not rows:
            continue

        headers = [
            cell.get_text(" ", strip=True)
            for cell in rows[0].find_all(
                ["th", "td"], recursive=False
            )
        ]

        for row in rows[1:]:
            cells = row.find_all(
                ["th", "td"], recursive=False
            )

            if len(cells) < 2:
                continue

            subject, level = extract_subject(
                cells[0].get_text(" ", strip=True)
            )

            for column_index, cell in enumerate(
                cells[1:], start=1
            ):
                header = (
                    headers[column_index]
                    if column_index < len(headers)
                    else ""
                )

                for link in cell.find_all("a", href=True):
                    pdf_url = urljoin(source_url, link["href"])
                    parsed = urlparse(pdf_url)

                    if parsed.hostname == "beta.etestavimas.lt":
                        continue

                    if not parsed.path.lower().endswith(".pdf"):
                        continue

                    
                    filename = unquote(parsed.path).split("/")[-1]

                    if pdf_url in seen:
                        continue

                    seen.add(pdf_url)

                    document_year = year

                    if document_year is None:
                        document_year = extract_year_from_filename(
                            filename,
                            pdf_url
                        )


                    doc_type = classify_document(
                        source_name, header, filename
                    )

                    
                    if doc_type == "excluded":
                        continue

                    document_session = extract_session(
                        filename, header
                    )

                    if document_session is None:
                        document_session = extract_session_from_filename(
                            filename
                        )


                    document = {
                        "year": document_year,
                        "subject": subject,
                        "exam_type": extract_exam_type(
                            source_name,
                            filename
                        ),
                        "session": document_session,
                        "srautas": None,
                        "dalis": extract_part(
                            header, filename
                        ),
                        "level": (
                            level
                            if source_name.startswith("VBE")
                            else None
                        ),
                        "document_type": doc_type,
                        "source": source_name,
                        "source_url": pdf_url,
                        "filename": filename,
                    }

                    documents.append(document)

    return documents

def collect_outside_table_documents(source_name, soup):
    """Collect PDF links outside HTML tables for review."""
    documents = []
    source_url = SOURCES[source_name]
    seen = set()

    for link in soup.find_all("a", href=True):
        # Skip links already handled by table parser
        if link.find_parent("table") is not None:
            continue

        pdf_url = urljoin(source_url, link["href"])
        parsed = urlparse(pdf_url)

        if not parsed.path.lower().endswith(".pdf"):
            continue

        if parsed.hostname == "beta.etestavimas.lt":
            continue

        if pdf_url in seen:
            continue

        seen.add(pdf_url)

        filename = unquote(parsed.path).split("/")[-1]

        # Use filename year only, avoid upload-date guessing
        match = re.search(
            r"(?<!\d)(20\d{2})(?!\d)",
            filename
        )
        year = int(match.group(1)) if match else None

        documents.append({
            "year": year,
            "subject": None,
            "exam_type": extract_exam_type(
                source_name, filename
            ),
            "session": extract_session(
                filename, ""
            ),
            "srautas": None,
            "dalis": extract_part("", filename),
            "level": None,
            "document_type": "review",
            "source": source_name,
            "source_url": pdf_url,
            "filename": filename,
            "link_text": link.get_text(" ", strip=True),
        })

    return documents


def main():
    print("=== NSA EXAM CRAWLER ===")

    all_documents = []

    for source_name, url in SOURCES.items():
        print("\nProcessing:", source_name)

        soup = fetch_page(url)

        if soup is None:
            continue

        if source_name == "VBE_answers":
            all_links = soup.find_all("a", href=True)

            pdf_links = [
                link for link in all_links
                if urlparse(
                    urljoin(url, link["href"])
                ).path.lower().endswith(".pdf")
            ]

            table_links = [
                link
                for table in soup.find_all("table")
                for link in table.find_all("a", href=True)
                if urlparse(
                    urljoin(url, link["href"])
                ).path.lower().endswith(".pdf")
            ]

            print("\n=== VBE ANSWERS DIAGNOSTICS ===")
            print("All PDF links:", len(pdf_links))
            print("PDF links inside tables:", len(table_links))
            print(
                "PDF links outside tables:",
                len(pdf_links) - len(table_links)
            )
        
        documents = collect_documents(source_name, soup)

        if source_name == "VBE_answers":
            outside_documents = collect_outside_table_documents(
                source_name, soup
            )

            existing_urls = {
                doc["source_url"] for doc in documents
            }

            for doc in outside_documents:
                if doc["source_url"] not in existing_urls:
                    documents.append(doc)
                    existing_urls.add(doc["source_url"])

        all_documents.extend(documents)

        print("Candidates collected:", len(documents))


    tasks = [
        doc for doc in all_documents
        if doc["document_type"] == "task"
    ]

    answers = [
        doc for doc in all_documents
        if doc["document_type"] == "answer"
    ]

    review = [
        doc for doc in all_documents
        if doc["document_type"] == "review"
    ]
    
    sample_tasks = [
        doc for doc in all_documents
        if doc["document_type"] == "sample_task"
    ]

    sample_answers = [
        doc for doc in all_documents
        if doc["document_type"] == "sample_answer"
    ]


    with (OUTPUT_DIR / "documents_preview.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(
            all_documents,
            file,
            ensure_ascii=False,
            indent=4,
        )

    print("\n=== SUMMARY ===")
    print("Total candidates:", len(all_documents))
    print("Tasks:", len(tasks))
    print("Answers:", len(answers))
    print("Review:", len(review))
    print("Sample tasks:", len(sample_tasks))
    print("Sample answers:", len(sample_answers))
    print("Missing year:", sum(
        doc["year"] is None for doc in all_documents
    ))
    print("Missing session:", sum(
        doc["session"] is None for doc in all_documents
    ))

    print("\nSaved: output/documents_preview.json")


if __name__ == "__main__":
    main()
