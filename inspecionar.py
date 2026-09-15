from curl_cffi import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
r = requests.get("https://lista.mercadolivre.com.br/fone", impersonate="chrome124", headers=headers)

soup = BeautifulSoup(r.text, "html.parser")
print("=== RAIO-X DOS 10 KB ===")
print("URL Final:", r.url)
print("Tamanho:", len(r.text))
print("Titulo:", soup.title.text.strip() if soup.title else "Sem titulo")
print("Texto da pagina:", " ".join(soup.text.split())[:300])

scripts = [s for s in soup.find_all("script") if "window.__PRELOADED_STATE__" in (s.string or "")]
print("Tem dados embutidos via Script (JSON):", len(scripts) > 0)
