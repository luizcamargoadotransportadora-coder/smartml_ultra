def eh_identico(termo, tit):
    t = set(re.sub(r'[^a-z0-9 ]', '', termo.lower()).split()) - {'de','do','da','para','com','em','e','o','a'}
    tit_l = tit.lower()
    if any(ac in tit_l for ac in ['capa','case','pelicula','cabo','carregador','adaptador'] if ac not in termo.lower()): return False
    return all(p in tit_l for p in t)

def eh_produto_identico(termo_busca: str, titulo_anuncio: str) -> bool:
    import unicodedata
    def normalizar(txt: str) -> str:
        txt = unicodedata.normalize('NFKD', txt).encode('ASCII', 'ignore').decode('utf-8')
        return re.sub(r'[^a-z0-9\s]', ' ', txt.lower())

    t_norm = normalizar(termo_busca)
    a_norm = normalizar(titulo_anuncio)

    # 1. Elimina acessorios se a busca for pelo produto principal
    acessorios = ["capa", "case", "pelicula", "peliculas", "cabo", "carregador", "adaptador", "suporte", "almofada", "borracha", "borrachinha", "cordao"]
    for ac in acessorios:
        if ac not in t_norm and re.search(r'' + re.escape(ac) + r'', a_norm):
            return False

    # 2. Remove stopwords comuns
    stopwords = {"de", "do", "da", "dos", "das", "para", "com", "em", "e", "ou", "o", "a", "os", "as", "um", "uma"}
    tokens_busca = [t for t in t_norm.split() if t and t not in stopwords]

    if not tokens_busca:
        return True

    # 3. Exige que todas as palavras-chave da busca estejam no titulo do concorrente
    tokens_anuncio = set(a_norm.split())
    for token in tokens_busca:
        if not any(token in tan for tan in tokens_anuncio):
            return False

    return True

import os
import re
import asyncio
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pw_instance = None
browser = None
browser_context = None
page_worker = None
lock = asyncio.Lock()

@app.on_event("startup")
async def startup():
    global pw_instance, browser, browser_context, page_worker
    pw_instance = await async_playwright().start()
    browser = await pw_instance.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )
    browser_context = await browser.new_context()
    page_worker = await browser_context.new_page()

@app.on_event("shutdown")
async def shutdown():
    global browser, pw_instance
    if browser:
        await browser.close()
    if pw_instance:
        await pw_instance.stop()

@app.get("/")
@app.get("/health")
def health():
    return {"status": "online", "worker": "SmartML Local Worker"}

async def executar_busca(termo: str, custo: float = 0.0):
    global page_worker, lock
    async with lock:
        try:
            termo_limpo = re.sub(r"[^\w\s-]", "", termo).strip().lower()
            termo_formatado = re.sub(r"\s+", "-", termo_limpo)
            url = f"https://lista.mercadolivre.com.br/{termo_formatado}"

            print(f"\n[ROBO] 🔍 Buscando: '{termo}' (Custo base: R$ {custo:.2f})")
            print(f"[ROBO] 🌐 Acessando URL: {url}")

            try:
                await page_worker.goto(url, wait_until="domcontentloaded", timeout=35000)
            except Exception as ge:
                print(f"[ROBO] ⚠️ Aviso de carregamento: {ge}")

            await page_worker.wait_for_timeout(2500)
            try:
                await page_worker.evaluate("window.scrollBy(0, 500)")
            except Exception:
                pass
            await page_worker.wait_for_timeout(1000)

            html = ""
            for _ in range(5):
                try:
                    await page_worker.wait_for_load_state("domcontentloaded", timeout=4000)
                    html = await page_worker.content()
                    if html:
                        break
                except Exception:
                    await page_worker.wait_for_timeout(1000)
            soup = BeautifulSoup(html, "html.parser")
            
            cards = soup.select(".poly-card, .ui-search-layout__item, div.ui-search-result__wrapper, .ui-search-result")
            print(f"[ROBO] 📦 Cards detectados na pagina: {len(cards)}")

            candidatos = []
            piso = (custo * 0.35) if custo > 0 else 5.0

            for card in cards:
                tag_tit = card.select_one(".poly-component__title, a.ui-search-link, .ui-search-item__title, h2, a.poly-card__title")
                if not tag_tit:
                    continue
                tit = tag_tit.get_text(strip=True)
                # Ignora produtos usados
                if any(u in card.get_text(" ", strip=True).lower() for u in ["usado", "usada", "recondicionado", "seminovo", "semi novo"]):
                    continue

                if not tit or len(tit) < 3:
                    continue

                tag_lnk = card.select_one("a[href*='mercadolivre.com.br'], a.ui-search-link, a.poly-component__title") or tag_tit
                lnk = tag_lnk.get("href", "") if tag_lnk.name == "a" else (card.find("a", href=True)["href"] if card.find("a", href=True) else "")

                tag_f = card.select_one(".andes-money-amount__fraction")
                if not tag_f:
                    continue
                try:
                    p = float(re.sub(r"[^\d]", "", tag_f.get_text(strip=True)))
                    tag_c = card.select_one(".andes-money-amount__cents")
                    if tag_c:
                        cents = re.sub(r"[^\d]", "", tag_c.get_text(strip=True))
                        if cents:
                            p += float(cents) / (10 ** len(cents))
                except Exception:
                    continue

                img_tag = card.select_one("img")
                foto = (img_tag.get("data-src") or img_tag.get("src") or "") if img_tag else ""

                if p >= piso and eh_produto_identico(termo, tit):
                    candidatos.append({"titulo": tit, "preco": p, "link": lnk, "imagem": foto})

            vistos = set()
            unicos = []
            for c in candidatos:
                chave = c["link"] if c["link"] else c["titulo"]
                if chave not in vistos:
                    vistos.add(chave)
                    unicos.append(c)

            unicos.sort(key=lambda x: x["preco"])
            print(f"[ROBO] ✅ Candidatos validos acima do piso (R$ {piso:.2f}): {len(unicos)}")
            if unicos:
                print(f"[ROBO] 🎯 Menor preco encontrado: R$ {unicos[0]['preco']:.2f} - {unicos[0]['titulo'][:40]}...")

            return {"sucesso": True, "candidatos": unicos[:20]}
        except Exception as e:
            print(f"[ROBO] ❌ Erro na busca: {e}")
            return {"sucesso": False, "candidatos": [], "mensagem": str(e)}

@app.get("/buscar")
@app.get("/scrape")
async def buscar_get(termo: str = "fone", custo: float = 0.0):
    return await executar_busca(termo, custo)

@app.post("/buscar")
@app.post("/scrape")
async def buscar_post(req: Request):
    dados = await req.json()
    termo = dados.get("termo") or dados.get("query") or "fone"
    custo = float(dados.get("custo") or 0.0)
    return await executar_busca(termo, custo)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8005)