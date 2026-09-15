import re

codigo_worker = '''import os, re, logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from curl_cffi import requests
from bs4 import BeautifulSoup
import uvicorn

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("smartml.worker")

app = FastAPI(title="SmartML Local Worker", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/buscar")
def buscar(termo: str, custo: float = 0.0):
    try:
        termo_limpo = re.sub(r"[^\w\s-]", "", termo).strip()
        termo_formatado = termo_limpo.replace(" ", "-")
        url = f"https://lista.mercadolivre.com.br/{termo_formatado}"
        log.info(f"Rastreando ML: {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        }

        r = requests.get(url, impersonate="chrome124", headers=headers, timeout=15)
        if r.status_code != 200:
            return {"sucesso": False, "candidatos": [], "mensagem": f"Status HTTP ML: {r.status_code}"}

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select(".poly-card, .ui-search-layout__item, div.ui-search-result__wrapper, .ui-search-result")

        candidatos = []
        piso = (custo * 0.35) if custo > 0 else 5.0

        for card in cards:
            tag_tit = card.select_one(".poly-component__title, a.ui-search-link, .ui-search-item__title, h2")
            if not tag_tit:
                continue
            tit = tag_tit.get_text(strip=True)

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
            except:
                continue

            img_tag = card.select_one("img.poly-component__picture, img.ui-search-result-image__element, img")
            foto = ""
            if img_tag:
                foto = img_tag.get("data-src") or img_tag.get("src") or ""

            if p >= piso:
                candidatos.append({
                    "titulo": tit,
                    "preco": p,
                    "link": lnk,
                    "imagem": foto
                })

            if len(candidatos) >= 30:
                break

        candidatos.sort(key=lambda x: x["preco"])
        return {"sucesso": True, "candidatos": candidatos[:20]}

    except Exception as e:
        log.error(f"Erro worker: {e}")
        return {"sucesso": False, "candidatos": [], "mensagem": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8005)
'''

with open("local_worker.py", "w", encoding="utf-8") as f:
    f.write(codigo_worker)

print(">>> local_worker.py atualizado com sucesso!")
