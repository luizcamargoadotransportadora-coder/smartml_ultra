import re, time, logging, os
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

log = logging.getLogger("smartml.scraper")
PERFIL_DIR = os.path.abspath("ml_perfil")

def _obter_driver():
    opts = uc.ChromeOptions()
    opts.add_argument(f"--user-data-dir={PERFIL_DIR}")
    opts.add_argument("--window-size=1280,850")
    driver = uc.Chrome(options=opts, version_main=152)
    return driver

def fazer_login():
    print("\nAbrindo o Chrome autenticado...")
    driver = _obter_driver()
    driver.get("https://www.mercadolivre.com.br")
    input("\n[!] Faca seu login ou resolva o captcha na janela aberta.\n[!] Quando terminar e estiver logado, volte aqui e aperte ENTER: ")
    driver.quit()
    print("\nSessao gravada com sucesso! Nao pedira mais login.")

def buscar_menor_preco_ml(termo, custo_base=0.0):
    termo_limpo = " ".join(re.sub(r"[^\w\s]", " ", termo).split())
    termo_slug = "-".join(termo_limpo.lower().split())
    url = f"https://lista.mercadolivre.com.br/{termo_slug}"
    driver = _obter_driver()
    try:
        driver.get(url)
        time.sleep(4)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.select(".poly-card, .ui-search-layout__item, div.ui-search-result__wrapper")
        anuncios = []
        ignorar = ["capa", "capinha", "pelicula", "película", "cabo", "carregador", "suporte", "fone", "adaptador", "case"]
        for card in cards:
            tag_tit = card.select_one(".poly-component__title, a.ui-search-link, .ui-search-item__title, h2")
            if not tag_tit: continue
            tit = tag_tit.get_text(strip=True)
            if any(x in tit.lower() for x in ignorar): continue
            tag_lnk = card.select_one("a[href*=\x27mercadolivre.com.br\x27]") or tag_tit
            lnk = tag_lnk.get("href", "") if tag_lnk.name == "a" else (card.find("a", href=True)["href"] if card.find("a", href=True) else "")
            tag_f = card.select_one(".andes-money-amount__fraction")
            if not tag_f: continue
            try:
                p = float(re.sub(r"[^\d]", "", tag_f.get_text(strip=True)))
                tag_c = card.select_one(".andes-money-amount__cents")
                if tag_c: p += float(re.sub(r"[^\d]", "", tag_c.get_text(strip=True))) / 100.0
            except:
                continue
            if p > 0: anuncios.append({"titulo": tit, "preco": p, "link": lnk})
        if not anuncios:
            return {"encontrado": False, "mensagem": f"Nenhum anuncio valido para {termo}."}
        if custo_base > 0:
            validos = [a for a in anuncios if a["preco"] >= (custo_base * 0.3)]
            if validos: anuncios = validos
        anuncios.sort(key=lambda x: x["preco"])
        m = anuncios[0]
        return {"encontrado": True, "menor_preco": m["preco"], "link": m["link"], "titulo_encontrado": m["titulo"]}
    except Exception as e:
        return {"encontrado": False, "mensagem": f"Erro automacao: {str(e)}"}
    finally:
        try:
            driver.quit()
        except:
            pass
