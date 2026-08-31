"""
SmartML Ultra - Price Discovery Engine v9.0 (Arquitetura API Meli Oficial)
"""
from __future__ import annotations
import json
import logging
import os
import re
import time
import unicodedata
import urllib.parse
from dataclasses import dataclass

from google import genai
from google.genai import types
from dotenv import load_dotenv
import requests

# Tratamento DevOps para rodar na nuvem (Linux) sem quebrar o winsound do notebook (Windows)
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("smartml.scraper")

# ============================================================ EFEITOS SONOROS
def som_campainha_meli():
    """Toca o áudio apenas se estiver rodando localmente no notebook."""
    if HAS_WINSOUND:
        try:
            arquivo_sucesso = os.path.join(os.getcwd(), "notificacao_meli.wav")
            winsound.PlaySound(arquivo_sucesso, winsound.SND_FILENAME | winsound.SND_ASYNC)
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
        if not api_key: return {"termo_busca": texto_bruto}
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
                model='gemini-1.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0)
            )
            return json.loads(response.text)
        except Exception:
            return {"termo_busca": texto_bruto, "palavras_veto": []}

class AuditorIAUltra:
    @staticmethod
    def auditar(termo_busca: str, titulo_anuncio: str, texto_card: str) -> dict:
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: return {"aprovado": False, "motivo": "Sem chave do Gemini", "confianca": "BAIXA"}
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Audite rigorosamente para e-commerce. Buscado: "{termo_busca}" | Título: "{titulo_anuncio}" | Card: "{texto_card}"
            Regras: Rejeite usados, vitrines, caixa aberta, acessórios (capa/película/caixa) ou divergência de modelo/capacidade.
            Responda EXATAMENTE JSON: {{"aprovado": true/false, "motivo": "motivo curto", "confianca": "ALTA"}}
            """
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0)
            )
            return json.loads(response.text)
        except Exception:
            return {"aprovado": False, "motivo": "Falha na API da IA", "confianca": "BAIXA"}

@dataclass
class Offer:
    title: str
    price: float
    permalink: str

# ============================================================ MOTOR PRINCIPAL DE DADOS
def buscar_menor_preco_ml(termo_busca: str, custo_compra: float = 0.0) -> dict:
    termo = str(termo_busca).strip()
    
    ia_data = ResolverIA.normalizar(termo)
    termo_limpo = ia_data.get("termo_busca", termo)
    
    log.info("[api] Buscando na Fonte Oficial: '%s'", termo_limpo)

    # 1. ACESSO DIRETO VIA API OFICIAL (Bypass de Cloudflare & 10x mais rápido)
    url_api = f"https://api.mercadolibre.com/sites/MLB/search?q={urllib.parse.quote(termo_limpo)}&condition=new"
    
    try:
        resp = requests.get(url_api, timeout=10)
        if resp.status_code != 200:
            return {"encontrado": False, "mensagem": "❌ ERRO DE COMUNICAÇÃO COM O ML."}
        dados = resp.json()
    except Exception as e:
        log.error("[api] Falha severa: %s", e)
        return {"encontrado": False, "mensagem": "❌ REDE DO SERVIDOR INOPERANTE."}
    
    resultados = dados.get("results", [])
    log.info("[api] Coletados %d itens brutos instantaneamente.", len(resultados))
    
    ofertas = []
    
    for item in resultados[:30]:  # Varredura profunda rápida
        titulo = item.get("title", "")
        preco = float(item.get("price", 0.0))
        link = item.get("permalink", "")
        
        if not titulo or preco <= 0: continue

        # 2. A PENEIRA MATEMÁTICA (Destrói capinhas sem gastar IA)
        if custo_compra > 0:
            limite_minimo = custo_compra * 0.25
            if preco < limite_minimo:
                log.info("[filtro_matematico] Lixo rejeitado: R$ %.2f - '%s'", preco, titulo[:30])
                continue

        # 3. FILTRO TEXTUAL DE SEGURANÇA
        texto_baixo = titulo.lower()
        lixo_obvio = ["recondicionado", "vitrine", "seminovo", "usado", "mostruário", "sucata", "caixa vazia"]
        if any(palavra in texto_baixo for palavra in lixo_obvio):
            continue

        # 4. A AUDITORIA FINA DA INTELIGÊNCIA ARTIFICIAL
        # Coleta atributos ricos do JSON da API para a IA ler
        attrs = ", ".join([f"{a.get('name')}: {a.get('value_name')}" for a in item.get("attributes", [])[:6]])
        texto_card = f"Preço: R$ {preco}. Especificações: {attrs}"
        
        auditoria = AuditorIAUltra.auditar(termo_limpo, titulo, texto_card)
        time.sleep(3) # Pausa estratégica vital para não tomar ban da cota gratuita do Gemini
        
        if not auditoria.get("aprovado", True):
            log.info("[auditor_ia] Rejeitado: '%s' | Motivo: %s", titulo[:40], auditoria.get("motivo"))
            continue

        ofertas.append(Offer(titulo, preco, link))
        log.info("[SUCESSO] Ativo validado: R$ %.2f - %s", preco, titulo[:40])
        
        # Assim que acha 3 reais concorrentes, cessa a busca para devolver o resultado pro celular.
        if len(ofertas) >= 3:
            break

    if ofertas:
        ofertas.sort(key=lambda x: x.price)
        menor = ofertas[0]
        
        log.info("🎯 RESULTADO ALCANÇADO! R$ %.2f", menor.price)
        som_campainha_meli()
        
        return {
            "encontrado": True,
            "menor_preco": menor.price,
            "link": menor.permalink,
            "titulo_encontrado": menor.title,
            "auditoria_ia": f"🤖 Motor API Meli | Amostra Blindada: {len(ofertas)}"
        }

    return {"encontrado": False, "diagnostico": "Zero compatibilidade.", "mensagem": "❌ PRODUTO NÃO ENCONTRADO PELA IA."}