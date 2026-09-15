from curl_cffi import requests
from bs4 import BeautifulSoup

def testar(nome, url, imp, h=None):
    try:
        r = requests.get(url, impersonate=imp, headers=h, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select(".poly-card, .ui-search-layout__item, div.ui-search-result__wrapper, .ui-search-result")
        bloqueado = "account-verification" in r.url or len(r.text) < 50000
        print(f"{nome}:")
        print(f"  Tamanho: {len(r.text)} bytes | Cards: {len(cards)} | Bloqueado: {bloqueado}")
    except Exception as e:
        print(f"{nome} -> Erro: {e}")

# 1. Simulacao Mobile (rotas mobile costumam ignorar a tela de account-verification de desktop)
h_mobile = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
    "Accept-Language": "pt-BR,pt;q=0.9"
}
testar("1. Mobile Safari", "https://lista.mercadolivre.com.br/fone", "safari17_0", h_mobile)

# 2. Rota NoIndex do proprio ML
testar("2. Parametro NoIndex", "https://lista.mercadolivre.com.br/fone_NoIndex_True", "chrome124")

# 3. Endpoint alternativo de busca do ML
testar("3. Rota /jm/search", "https://www.mercadolivre.com.br/jm/search?as_word=fone", "chrome124")
