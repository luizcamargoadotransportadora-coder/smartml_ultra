import re, logging
from bs4 import BeautifulSoup
from curl_cffi import requests

log = logging.getLogger("smartml.scraper")

def buscar_menor_preco_ml(termo, custo_base=0.0):
    try:
        termo_limpo = " ".join(re.sub(r"[^\w\s]", " ", termo).split())
        termo_slug = "-".join(termo_limpo.lower().split())
        url = f"https://lista.mercadolivre.com.br/{termo_slug}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Cookie": "country_id=MLB; currency_id=BRL; c_country=BR"
        }

        r = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        page_title = soup.title.text.strip() if soup.title else "Sem titulo"
        body_text = " ".join(soup.body.get_text().split())[:250] if soup.body else ""
        
        cards = soup.select(".poly-card, .ui-search-layout__item, div.ui-search-result__wrapper")
        anuncios = []
        ignorar = ["capa", "capinha", "pelicula", "película", "cabo", "carregador", "suporte", "adaptador", "case"]

        for card in cards:
            tag_tit = card.select_one(".poly-component__title, a.ui-search-link, .ui-search-item__title, h2")
            if not tag_tit:
                continue
            tit = tag_tit.get_text(strip=True)
            if any(x in tit.lower() for x in ignorar):
                continue

            tag_lnk = card.select_one("a[href*='mercadolivre.com.br']") or tag_tit
            lnk = tag_lnk.get("href", "") if tag_lnk.name == "a" else (card.find("a", href=True)["href"] if card.find("a", href=True) else "")

            tag_f = card.select_one(".andes-money-amount__fraction")
            if not tag_f:
                continue

            try:
                p = float(re.sub(r"[^\d]", "", tag_f.get_text(strip=True)))
                tag_c = card.select_one(".andes-money-amount__cents")
                if tag_c:
                    p += float(re.sub(r"[^\d]", "", tag_c.get_text(strip=True))) / 100.0
            except Exception:
                continue

            if p > 0:
                anuncios.append({"titulo": tit, "preco": p, "link": lnk})

        if not anuncios:
            return {
                "encontrado": False, 
                "mensagem": f"Cards: {len(cards)} | Titulo: {page_title} | Trecho: {body_text}"
            }

        if custo_base > 0:
            validos = [a for a in anuncios if a["preco"] >= (custo_base * 0.3)]
            if validos:
                anuncios = validos

        anuncios.sort(key=lambda x: x["preco"])
        m = anuncios[0]
        return {"encontrado": True, "menor_preco": m["preco"], "link": m["link"], "titulo_encontrado": m["titulo"]}

    except Exception as e:
        log.error(f"Erro scraper: {e}")
        return {"encontrado": False, "mensagem": f"Erro automacao: {str(e)}"}
