"""
SmartML Ultra - Price Discovery Engine v8.6 (Áudio Oficial do Usuário)
"""
from __future__ import annotations
import json
import logging
import os
import re
import statistics
import time
import unicodedata
import urllib.parse
import winsound
from dataclasses import dataclass

from google import genai
from google.genai import types
from dotenv import load_dotenv

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("smartml.scraper")

FRONT = "https://lista.mercadolivre.com.br"

# ============================================================ EFEITOS SONOROS
def som_alerta_bloqueio():
    """Toca o som de Erro direto da pasta do Windows para alertar CAPTCHA."""
    try:
        arquivo_erro = r"C:\Windows\Media\Windows Critical Stop.wav"
        winsound.PlaySound(arquivo_erro, winsound.SND_FILENAME)
    except: pass

def som_campainha_meli():
    """Toca O SEU arquivo de áudio original do Mercado Livre."""
    try:
        # Aponta exatamente para o nome do arquivo que você forneceu
        arquivo_sucesso = os.path.join(os.getcwd(), "notificacao_meli.wav")
        winsound.PlaySound(arquivo_sucesso, winsound.SND_FILENAME)
    except Exception as e: 
        log.error(f"[audio] Erro ao tocar som: {e}")

# ============================================================ UTILITÁRIOS
def strip_accents(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))

def norm(t: str) -> str:
    t = strip_accents(t or "").lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

# ============================================================ INTELIGÊNCIA ARTIFICIAL
class ResolverIA:
    @staticmethod
    def normalizar(texto_bruto: str) -> dict:
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: return {}
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Você é um normalizador de identificação de produtos para e-commerce. 
            Extraia os dados do texto abaixo EXATAMENTE neste formato JSON:
            {{
                "termo_busca": "String limpa e corrigida",
                "palavras_veto": ["lista", "de", "palavras", "acessorios", "ou", "sucata", "para", "excluir"]
            }}
            Regras: Extraia apenas o que está no texto. Corrija erros. Padronize grandezas (ex: 256 GB). 
            Se indicar acessório, capinha ou sucata, coloque em 'palavras_veto'. Responda APENAS JSON.
            Texto: "{texto_bruto}"
            """
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0)
            )
            return json.loads(response.text)
        except Exception as e:
            log.warning(f"[ia] API falhou no normalizador. Ativando Plano B de limpeza...")
            vetos_comuns = ["capinha", "pelicula", "sucata", "caixa", "acessorio", "defeito"]
            termo_limpo = texto_bruto
            vetos_encontrados = []
            
            for veto in vetos_comuns:
                if veto in termo_limpo.lower():
                    vetos_encontrados.append(veto)
                    termo_limpo = re.sub(fr'\b{veto}\b', '', termo_limpo, flags=re.IGNORECASE)
            
            termo_limpo = re.sub(r'\s+', ' ', termo_limpo).replace(' e ', ' ').strip()
            return {"termo_busca": termo_limpo, "palavras_veto": vetos_encontrados}

class AuditorIAUltra:
    @staticmethod
    def auditar(termo_busca: str, titulo_anuncio: str, texto_card: str) -> dict:
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: return {"aprovado": False, "motivo": "Sem chave", "confianca": "BAIXA"}
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Audite rigorosamente para e-commerce. Buscado: "{termo_busca}" | Título: "{titulo_anuncio}" | Card: "{texto_card}"
            Regras: Rejeite usados, vitrines, caixa aberta, acessórios (capa/película) ou divergência de modelo/capacidade.
            Responda EXATAMENTE JSON: {{"aprovado": true/false, "motivo": "motivo curto", "confianca": "ALTA"}}
            """
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0)
            )
            return json.loads(response.text)
        except Exception:
            return {"aprovado": False, "motivo": "Bloqueio preventivo por falha na API", "confianca": "BAIXA"}

# ============================================================ NAVEGADOR
class BrowserManager:
    _instance = None
    @classmethod
    def get_instance(cls):
        if cls._instance is None: cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.driver = None
        self.iniciar_driver()

    def iniciar_driver(self):
        if self.driver: 
            try: self.driver.quit()
            except: pass
        
        opts = uc.ChromeOptions()
        opts.add_argument("--start-maximized")
        profile_dir = os.path.join(os.getcwd(), "chrome_profile")
        
        log.info("Iniciando Undetected Chromedriver...")
        self.driver = uc.Chrome(options=opts, user_data_dir=profile_dir, version_main=151)

    def buscar_pagina(self, url: str):
        self.driver.get(url)
        time.sleep(3.5)
        
        html_page = self.driver.page_source.lower()
        if "captcha" in html_page or "verificação" in html_page or "account-verification" in self.driver.current_url.lower():
            log.warning("⚠️ ALERTA: ROBÔ DETECTADO! Intervenção humana necessária.")
            som_alerta_bloqueio()
            time.sleep(15)

@dataclass
class Offer:
    title: str
    price: float
    permalink: str

# ============================================================ MOTOR PRINCIPAL
def buscar_menor_preco_ml(termo_busca: str, custo_compra: float = 0.0) -> dict:
    termo = str(termo_busca).strip()
    
    ia_data = ResolverIA.normalizar(termo)
    termo_limpo = ia_data.get("termo_busca", termo)
    vetos = ia_data.get("palavras_veto", [])
    
    log.info("[ia] Termo limpo: '%s' | Vetos: %s", termo_limpo, vetos)

    browser = BrowserManager.get_instance()
    slug = urllib.parse.quote(norm(termo_limpo).replace(" ", "-"))
    url_alvo = f"{FRONT}/{slug}"
    
    log.info("[selenium] Acessando URL: %s", url_alvo)
    browser.buscar_pagina(url_alvo)
    
    elementos = browser.driver.find_elements(
        By.CSS_SELECTOR, 
        "div.poly-card, li.ui-search-layout__item, div.ui-search-result__wrapper, div.andes-card"
    )
    log.info("[selenium] Elementos brutos encontrados: %d", len(elementos))
    
    ofertas = []
    for idx, el in enumerate(elementos[:3]):
        try:
            texto = el.text
            if not texto or "indisponível" in texto.lower() or "esgotado" in texto.lower():
                continue

            titulo = ""
            for sel_tit in ["a.poly-component__title", "h2.ui-search-item__title", "h2.poly-box", "h2"]:
                try:
                    el_t = el.find_element(By.CSS_SELECTOR, sel_tit)
                    if el_t.text:
                        titulo = el_t.text; break
                except: continue
            
            if not titulo: continue

            texto_baixo = texto.lower()
            lixo_obvio = ["recondicionado", "vitrine", "seminovo", "usado", "mostruário", "sucata", "caixa aberta"]
            if any(palavra in texto_baixo for palavra in lixo_obvio):
                log.info("[filtro_local] Rejeitado (Lixo óbvio): '%s'", titulo[:40])
                continue

            auditoria = AuditorIAUltra.auditar(termo_limpo, titulo, texto)
            if not auditoria.get("aprovado", True):
                log.info("[auditor] Rejeitado: '%s' | Motivo: %s", titulo[:40], auditoria.get("motivo"))
                continue

            preco = 0.0
            matches_preco = re.findall(r"R\$\s*([\d\.]+)(?:,(\d{2}))?", texto)
            if matches_preco:
                lista = []
                for m in matches_preco:
                    val = float(f"{m[0].replace('.', '')}.{m[1] if m[1] else '00'}")
                    if val > 100: lista.append(val)
                if lista: preco = min(lista)
            
            if preco <= 0: continue

            link = ""
            for sel_link in ["a.poly-component__title", "a.ui-search-link", "a"]:
                try:
                    el_l = el.find_element(By.CSS_SELECTOR, sel_link)
                    href = el_l.get_attribute("href")
                    if href and "mercadolivre.com.br" in href and "lista.mercadolivre" not in href:
                        link = href; break
                except: continue

            if not link: continue

            ofertas.append(Offer(titulo, preco, link.split('?')[0]))
            time.sleep(4) # Pausa de 4s para respeitar o limite gratuito da API
            
        except Exception:
            continue

    if ofertas:
        ofertas.sort(key=lambda x: x.price)
        prices = [o.price for o in ofertas]
        
        log.info("🎯 OPORTUNIDADE ENCONTRADA! Tocando campainha...")
        som_campainha_meli()
        
        return {
            "encontrado": True,
            "menor_preco": min(prices),
            "link": ofertas[0].permalink,
            "titulo_encontrado": ofertas[0].title,
            "auditoria_ia": f"🤖 Híbrido IA Blindada | Amostra: {len(prices)}"
        }

    return {"encontrado": False, "diagnostico": "Nenhum anúncio válido", "mensagem": "❌ PRODUTO NÃO ENCONTRADO."}