import re, uvicorn
from fastapi import FastAPI, Query
from bs4 import BeautifulSoup
from curl_cffi import requests

app = FastAPI(title="SmartML Local Worker - Imagens e Vendas")

@app.get("/buscar")
def buscar(termo: str = Query(...), custo: float = Query(0.0)):
    try:
        termo_limpo = " ".join(re.sub(r"[^\w\s]", " ", termo).split())
        termo_slug = "-".join(termo_limpo.lower().split())
        url = f"https://lista.mercadolivre.com.br/{termo_slug}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9"
        }

        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select(".poly-card, .ui-search-layout__item, div.ui-search-result__wrapper")

        candidatos = []
        piso = (custo * 0.4) if custo > 0 else 5.0

        for card in cards:
            tag_tit = card.select_one(".poly-component__title, a.ui-search-link, .ui-search-item__title, h2")
            if not tag_tit:
                continue
            tit = tag_tit.get_text(strip=True)

            # Filtro de avaliacao / vendas comprovadas
            tag_rev = card.select_one(".poly-reviews__total, .ui-search-reviews__amount, span.andes-visually-hidden")
            tag_stars = card.select_one(".poly-reviews, .ui-search-reviews")
            if not tag_rev and not tag_stars:
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

            # Captura da foto em alta definicao do anuncio
            img_tag = card.select_one("img.poly-component__picture, img.ui-search-result-image__element, img")
            foto = ""
            if img_tag:
                foto = img_tag.get("data-src") or img_tag.get("src") or ""
                if foto.startswith("data:image"):
                    foto = img_tag.get("data-src", "")

            if p >= piso:
                candidatos.append({"titulo": tit, "preco": p, "link": lnk, "imagem": foto})

            if len(candidatos) >= 30:
                break

        candidatos.sort(key=lambda x: x["preco"])
        return {"sucesso": True, "candidatos": candidatos[:20]}

    except Exception as e:
        return {"sucesso": False, "candidatos": [], "mensagem": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8005)
