
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
from pathlib import Path

URL = (
    "https://www.nsa.smsm.lt/pasiekimu-departamentas/"
    "egzaminai-ir-pasiekimu-patikrinimai/"
    "valstybiniai-brandos-egzaminai/"
    "egzaminu-uzduotys/"
)

# Папка для скачанных файлов
DOWNLOAD_FOLDER = Path("downloads")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

print("Connecting to NSA website...")

try:
    response = requests.get(URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    links = soup.find_all("a", href=True)

    pdf_links = set()

    for link in links:
        full_url = urljoin(URL, link["href"])
        filename = unquote(urlparse(full_url).path).lower()

        if not filename.endswith(".pdf"):
            continue

        if "beta.etestavimas.lt" in urlparse(full_url).netloc.lower():
            continue

        # Исключаем пустые бланки ответов
        if "atsakymu-lapas" in filename or "atsakymų-lapas" in filename:
            continue

        pdf_links.add(full_url)

    print("PDF candidates found:", len(pdf_links))

    # Пока скачиваем только первые 3 файла
    for index, pdf_url in enumerate(sorted(pdf_links)[:3], start=1):
        filename = Path(unquote(urlparse(pdf_url).path)).name
        file_path = DOWNLOAD_FOLDER / filename

        print(f"\nDownloading {index}: {filename}")

        try:
            pdf_response = requests.get(pdf_url, timeout=60)
            pdf_response.raise_for_status()

            # Проверяем, что ответ похож на PDF
            if not pdf_response.content.startswith(b"%PDF-"):
                print("Skipped: response is not a valid PDF")
                continue

            file_path.write_bytes(pdf_response.content)
            print("Saved:", file_path)

        except requests.RequestException as error:
            print("Download error:", error)

    print("\nTest download finished!")

except requests.RequestException as error:
    print("Website connection error:", error)
