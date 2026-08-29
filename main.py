"""
SmartML Ultra - API Principal (FastAPI)
Motor de Buybox e Scraping Integrados.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import urllib.request
import json

from src.config_loader import carregar_config
from src.scraper import buscar_menor_preco_ml

app = FastAPI(title="SmartML Ultra API", version="100.4")
cfg = carregar_config()

class RequisicaoAnalise(BaseModel):
    titulo: str
    custo: float

def round2(n):
    return round(n + 1e-9, 2)

@app.get("/")
def health_check():
    return {"status": "online", "projeto": "SmartML Ultra", "versao": "100.4"}

@app.post("/analisar")
def analisar_produto(req: RequisicaoAnalise):
    try:
        # 1. Scraping NLP de Alta Precisão
        dados_mercado = buscar_menor_preco_ml(req.titulo, req.custo)
        
        if not dados_mercado.get("encontrado"):
            return {
                "sucesso": False, 
                "mensagem": "❌ PRODUTO NÃO ENCONTRADO PELA IA.<br><br>Cole o <b>LINK EXATO</b> do Mercado Livre no campo de busca para precisão absoluta."
            }

        menor_preco = float(dados_mercado["menor_preco"])
        if menor_preco <= 0:
            return {"sucesso": False, "mensagem": "❌ Preço de concorrente inválido capturado."}

        # 2. Matemática Contábil (Buybox Real)
        pb = round2(menor_preco * 0.98)
        pc = round2(menor_preco * 0.94)
        custo = req.custo
        
        # Premium
        cp_brl = round2(pb * 0.165)
        ip_brl = round2(pb * 0.06)
        tf_p = 6.0 if pb < 79 else 0.0
        fr_p = 18.5 if pb >= 79 else 0.0
        avarias = round2(custo * 0.015)
        ct_p = round2(custo + cp_brl + tf_p + fr_p + ip_brl + 1.0 + 2.5 + avarias)
        lucro_p = round2(pb - ct_p)
        margem_p = round2((lucro_p / pb) * 100) if pb > 0 else 0
        
        # Classico
        cc_brl = round2(pc * 0.115)
        ic_brl = round2(pc * 0.06)
        tf_c = 6.0 if pc < 79 else 0.0
        fr_c = 18.5 if pc >= 79 else 0.0
        ct_c = round2(custo + cc_brl + tf_c + fr_c + ic_brl + 1.0 + 2.5 + avarias)
        lucro_c = round2(pc - ct_c)
        margem_c = round2((lucro_c / pc) * 100) if pc > 0 else 0

        # Veredito
        lucro_min = 150.0 if custo >= 3000 else (60.0 if custo >= 500 else 15.0)
        status = "A"
        if lucro_p <= 0 and lucro_c <= 0:
            status = "E"
        elif lucro_p < lucro_min or margem_p < 4.0:
            status = "D"

        return {
            "sucesso": True,
            "titulo": dados_mercado.get("titulo_encontrado", req.titulo),
            "menor_preco": menor_preco,
            "link": dados_mercado["link"],
            "premium": {
                "preco": pb, "comissao": cp_brl, "taxa_fixa": tf_p, "frete": fr_p, "imposto": ip_brl,
                "nf": 1.0, "emb": 2.5, "avarias": avarias, "custo_total": ct_p, "lucro": lucro_p, "margem": margem_p
            },
            "classico": {
                "preco": pc, "comissao": cc_brl, "taxa_fixa": tf_c, "frete": fr_c, "imposto": ic_brl,
                "custo_total": ct_c, "lucro": lucro_c, "margem": margem_c
            },
            "status": status
        }
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Erro interno no servidor: {str(e)}"}