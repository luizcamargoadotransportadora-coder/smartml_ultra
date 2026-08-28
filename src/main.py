"""
SmartML Ultra v100.0 - API de Porta de Entrada (FastAPI)
Processa requisições HTTP locais para o motor contábil e logístico.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.config_loader import carregar_config
from src.motor import processar

app = FastAPI(
    title="SmartML Ultra API",
    version="100.1",
    description="Motor de arbitragem contábil e precificação Mercado Livre"
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
    return {"status": "online", "projeto": "SmartML Ultra", "versao": "100.1"}

@app.post("/analisar")
def analisar_produto(req: RequisicaoAnalise):
    try:
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
        return resultado.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, description=str(e))