"""
SmartML Ultra - FastAPI Main Controller v11.2
Interface Web + Auditoria ML + Gemini Vision Universal
"""
import os
import re
import json
import io
import base64
import logging
import urllib.request
import urllib.error
from PIL import Image
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.scraper import buscar_menor_preco_ml
from src.database import salvar_analise

app = FastAPI(title="Smart Meli Ultra API", version="11.2")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("smartml.main")

GEMINI_API_KEY = base64.b64decode("QVEuQWI4Uk42Snk1Q2JsTmdvUzBKbG9UQmMzYU1IZU9DX3hMNWY5QWJwVDZuRnBiLTNmdGc=").decode("utf-8")

@app.get("/")
def abrir_aplicativo():
    caminho_html = os.path.join(os.getcwd(), "static", "index.html")
    if os.path.exists(caminho_html):
        return FileResponse(caminho_html)
    return {"erro": "Arquivo static/index.html não encontrado no servidor."}

class EntradaImagem(BaseModel):
    imagem_base64: str

@app.post("/reconhecer-imagem")
def reconhecer_imagem(entrada: EntradaImagem):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"
    
    base64_data = entrada.imagem_base64
    if "," in base64_data:
        base64_data = base64_data.split(",")[1]

    # Pipeline de compressão rápida
    try:
        img_bytes = base64.b64decode(base64_data)
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((1024, 1024))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80, optimize=True)
        base64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as img_err:
        log.warning(f"Aviso compressao: {img_err}")

    prompt = (
        "Identifique o produto comercial nesta imagem (eletrônicos, perfumes, cosméticos, bebidas, ferramentas ou utilidades em geral). "
        "Retorne APENAS a marca, a linha/modelo e a especificação essencial (como volume, capacidade ou versão) para busca direta no Mercado Livre. "
        "Exemplos: 'Perfume Sauvage Dior EDP 100ml', 'Whisky Black Label 1L', 'Galaxy S23 256GB', 'Stanley Garrafa Térmica 1.4L', 'Parafusadeira Bosch GSB 18V'. "
        "NÃO escreva introduções, NÃO use palavras como caixa, embalagem, original, lacrado, novo ou importado."
    )

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64_data
                    }
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.1
        }
    }

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY.strip()
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=90) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            texto_bruto = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            texto_limpo = re.sub(r'[`"\'*_\n\r\t]', ' ', texto_bruto)
            texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()
            
            for prefixo in ["produto:", "modelo:", "item:", "marca:"]:
                if texto_limpo.lower().startswith(prefixo):
                    texto_limpo = texto_limpo[len(prefixo):].strip()

            log.info(f"Termo extraído pela IA: {texto_limpo}")
            return {"sucesso": True, "produto": texto_limpo}
            
    except urllib.error.HTTPError as he:
        err_msg = he.read().decode("utf-8")
        log.error(f"Erro HTTP Gemini ({he.code}): {err_msg}")
        return {"sucesso": False, "mensagem": f"Erro Google ({he.code}): {err_msg[:120]}"}
    except Exception as e:
        log.error(f"Falha de conexão com Gemini: {e}")
        return {"sucesso": False, "mensagem": f"Erro: {str(e)}"}

class EntradaAnalise(BaseModel):
    titulo: str
    custo: float

@app.post("/analisar")
def analisar_produto(entrada: EntradaAnalise):
    try:
        log.info(f"Iniciando auditoria: {entrada.titulo} | Custo: R$ {entrada.custo}")
        
        resultado_scraper = buscar_menor_preco_ml(entrada.titulo, entrada.custo)
        
        if not resultado_scraper.get("encontrado"):
            return {
                "sucesso": False,
                "mensagem": resultado_scraper.get("mensagem", "❌ PRODUTO NÃO ENCONTRADO.")
            }

        menor_preco = resultado_scraper["menor_preco"]
        link = resultado_scraper["link"]
        titulo_encontrado = resultado_scraper["titulo_encontrado"]

        comissao_classico = menor_preco * 0.115
        comissao_premium = menor_preco * 0.165
        taxa_fixa = 6.0 if menor_preco < 79 else 0.0
        frete_estimado = 18.0 if menor_preco < 79 else 0.0
        imposto = menor_preco * 0.06
        nf = menor_preco * 0.01
        emb = 2.0
        avarias = menor_preco * 0.015

        custo_total_premium = entrada.custo + comissao_premium + taxa_fixa + frete_estimado + imposto + nf + emb + avarias
        lucro_premium = menor_preco - custo_total_premium
        margem_premium = (lucro_premium / menor_preco) * 100 if menor_preco > 0 else 0

        custo_total_classico = entrada.custo + comissao_classico + taxa_fixa + frete_estimado + imposto + nf + emb + avarias
        lucro_classico = menor_preco - custo_total_classico
        margem_classico = (lucro_classico / menor_preco) * 100 if menor_preco > 0 else 0

        status = "A" if margem_premium >= 15 else ("E" if lucro_premium < 0 else "D")

        resposta_final = {
            "sucesso": True,
            "titulo": titulo_encontrado,
            "menor_preco": menor_preco,
            "link": link,
            "status": status,
            "classico": {
                "preco": menor_preco,
                "comissao": comissao_classico,
                "taxa_fixa": taxa_fixa,
                "frete": frete_estimado,
                "imposto": imposto,
                "nf": nf,
                "emb": emb,
                "avarias": avarias,
                "custo_total": custo_total_classico,
                "lucro": lucro_classico,
                "margem": round(margem_classico, 2)
            },
            "premium": {
                "preco": menor_preco,
                "comissao": comissao_premium,
                "taxa_fixa": taxa_fixa,
                "frete": frete_estimado,
                "imposto": imposto,
                "nf": nf,
                "emb": emb,
                "avarias": avarias,
                "custo_total": custo_total_premium,
                "lucro": lucro_premium,
                "margem": round(margem_premium, 2)
            }
        }

        try:
            dados_banco = {
                "titulo_original": entrada.titulo,
                "titulo_encontrado": titulo_encontrado,
                "custo_base": entrada.custo,
                "moeda": "BRL",
                "menor_preco": menor_preco,
                "link": link,
                "classico": resposta_final["classico"],
                "premium": resposta_final["premium"],
                "status": status,
                "origem": "WebApp",
                "confianca": "ALTA"
            }
            salvar_analise(dados_banco)
        except Exception as db_err:
            log.warning(f"Aviso SQLite: {db_err}")

        return resposta_final

    except Exception as e:
        log.error(f"Erro no processamento da análise: {e}")
        raise HTTPException(status_code=500, detail=str(e))
