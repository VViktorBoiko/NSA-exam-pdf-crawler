
import requests
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

count = 0

for link in soup.find_all("a", href=True):
    full_url = urljoin(URL, link["href"])
    filename = unquote(urlparse(full_url).path)

    if not filename.lower().endswith(".pdf"):
        continue

    if "beta.etestavimas.lt" in urlparse(full_url).netloc.lower():
        continue

    # Показываем название ссылки и ближайший контекст
    link_text = link.get_text(" ", strip=True)

    row = link.find_parent("tr")
    row_text = row.get_text(" ", strip=True) if row else ""

    print("=" * 70)
    print("FILE:", filename.split("/")[-1])
    print("LINK TEXT:", link_text)
    print("ROW CONTEXT:", row_text[:400])
    print("URL:", full_url)

    count += 1

    if count >= 10:
        break

print("\nInspected:", count, "PDF links")
