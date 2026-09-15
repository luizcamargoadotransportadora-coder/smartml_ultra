from curl_cffi import requests
from bs4 import BeautifulSoup

s = requests.Session(impersonate="chrome124")

# 1. Visita a home para coletar cookies reais de sessao
r_home = s.get("https://www.mercadolivre.com.br/")
print("Status Home:", r_home.status_code)
print("Cookies coletados:", len(s.cookies))

# 2. Busca simulando vinda organica
headers = {
    "Referer": "https://www.google.com/",
    "Accept-Language": "pt-BR,pt;q=0.9"
}
r = s.get("https://lista.mercadolivre.com.br/fone", headers=headers)
print("Tamanho HTML da busca:", len(r.text))

soup = BeautifulSoup(r.text, "html.parser")
cards = soup.select(".poly-card, .ui-search-layout__item, div.ui-search-result__wrapper")
print("Cards detectados:", len(cards))
