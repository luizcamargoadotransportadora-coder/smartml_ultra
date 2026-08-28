"""
SmartML Ultra - API Principal (FastAPI + Scraper de Precisão)
Integra a porta de entrada HTTP com o motor contábil e o buscador NLP do Mercado Livre.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.config_loader import carregar_config
from src.motor import processar
from src.scraper import buscar_menor_preco_ml

app = FastAPI(
    title="SmartML Ultra API",
    version="100.2",
    description="Motor de arbitragem contábil e precificação Mercado Livre com IA de Precisão"
)

# Carrega a configuração centralizada do YAML uma única vez na inicialização
cfg = carregar_config()

class RequisicaoAnalise(BaseModel):
    titulo: str
    custo: float
    moeda: Optional[str] = "BRL"
    categoria: Optional[str] = None
    peso_kg: Optional[float] = 0.5
    comprimento_cm: Optional[float] = 20.0
    largura_cm: Optional[float] = 15.0
    altura_cm: Optional[float] = 10.0

@app.get("/")
def health_check():
    return {"status": "online", "projeto": "SmartML Ultra", "versao": "100.2"}

@app.post("/analisar")
def analisar_produto(req: RequisicaoAnalise):
    try:
        # 1. Executa a varredura inteligente no Mercado Livre via Scraper (Auditoria NLP)
        dados_mercado = buscar_menor_preco_ml(req.titulo, req.custo)
        
        menor_preco_concorrente = 0.0
        link_concorrente = ""
        auditoria_msg = "Sem concorrente exato encontrado."

        if dados_mercado.get("encontrado"):
            menor_preco_concorrente = dados_mercado["menor_preco"]
            link_concorrente = dados_mercado["link"]
            auditoria_msg = dados_mercado["auditoria_ia"]
        else:
            # Fallback matemático caso o produto seja muito específico ou offline
            menor_preco_concorrente = round(req.custo * 1.35, 2)
            link_concorrente = f"https://lista.mercadolivre.com.br/{req.titulo.lower().replace(' ', '-')}"
            auditoria_msg = "⚠️ Concorrente exato não localizado. Simulação teórica (Markup)."

        # 2. Processa a precificação contábil através do nosso motor blindado
        resultado = processar(
            cfg=cfg,
            titulo=req.titulo,
            custo=req.custo,
            moeda=req.moeda,
            categoria=req.categoria,
            peso_kg=req.peso_kg,
            comprimento_cm=req.comprimento_cm,
            largura_cm=req.largura_cm,
            altura_cm=req.altura_cm
        )
        
        # Converte o resultado para dicionário e injeta os dados reais do concorrente auditado
        resposta_final = resultado.to_dict()
        resposta_final["auditoria_mercado"] = {
            "encontrado": dados_mercado.get("encontrado", False),
            "menor_preco": menor_preco_concorrente,
            "link_direto": link_concorrente,
            "parecer_ia": auditoria_msg
        }

        return resposta_final

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))