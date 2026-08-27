"""
SmartML Ultra v100.1 - API HTTP (FastAPI)
Envelopamento do motor de cálculo para execução local e integração com AppSheet/Webhooks.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Garante que a pasta 'src' esteja acessível para importação
RAIZ = Path(__file__).resolve().parent
SRC = RAIZ / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from config_loader import carregar_config
import motor

app = FastAPI(
    title="SmartML Ultra API",
    version="100.1",
    description="API de Precificação Multimoeda, Frete Real e Classificação de Viabilidade"
)

# Habilita CORS para permitir conexões do AppSheet e navegadores
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carrega a configuração na inicialização
try:
    cfg = carregar_config()
except Exception as e:
    cfg = None
    print(f"[AVISO] Falha ao carregar config inicial: {e}")


class ProdutoInput(BaseModel):
    titulo: str = Field(..., description="Nome ou descrição do produto")
    custo: float = Field(..., gt=0, description="Custo na moeda de origem")
    moeda: str = Field(default="USD", description="Moeda de origem: USD, PYG ou BRL")
    categoria: Optional[str] = Field(default=None, description="Categoria opcional para comissão")
    peso_kg: float = Field(default=0.5, gt=0, description="Peso real em kg")
    comprimento_cm: float = Field(default=20.0, gt=0, description="Comprimento em cm")
    largura_cm: float = Field(default=15.0, gt=0, description="Largura em cm")
    altura_cm: float = Field(default=10.0, gt=0, description="Altura em cm")
    estrategia: str = Field(default="equilibrado", description="Estratégia: 'equilibrado' ou 'lucro'")


class LoteInput(BaseModel):
    produtos: List[ProdutoInput]


@app.get("/")
def health_check() -> Dict[str, str]:
    """Endpoint de checagem de integridade do serviço."""
    return {
        "status": "online",
        "sistema": "SmartML Ultra",
        "versao": "100.1"
    }


@app.post("/analisar")
def analisar_produto(dados: ProdutoInput) -> Dict[str, Any]:
    """Processa um produto individual e retorna a análise completa com faixas e recomendação."""
    global cfg
    if cfg is None:
        cfg = carregar_config()

    try:
        resultado = motor.processar(
            cfg=cfg,
            titulo=dados.titulo,
            custo=dados.custo,
            moeda=dados.moeda,
            categoria=dados.categoria,
            peso_kg=dados.peso_kg,
            comprimento_cm=dados.comprimento_cm,
            largura_cm=dados.largura_cm,
            altura_cm=dados.altura_cm,
            estrategia=dados.estrategia
        )
        return resultado.to_dict()
    except Exception as erro:
        raise HTTPException(status_code=500, detail=f"Erro no processamento do motor: {str(erro)}")


@app.post("/analisar-lote")
def analisar_lote(lote: LoteInput) -> List[Dict[str, Any]]:
    """Processa múltiplos produtos em uma única requisição."""
    global cfg
    if cfg is None:
        cfg = carregar_config()

    respostas = []
    for item in lote.produtos:
        try:
            res = motor.processar(
                cfg=cfg,
                titulo=item.titulo,
                custo=item.custo,
                moeda=item.moeda,
                categoria=item.categoria,
                peso_kg=item.peso_kg,
                comprimento_cm=item.comprimento_cm,
                largura_cm=item.largura_cm,
                altura_cm=item.altura_cm,
                estrategia=item.estrategia
            )
            respostas.append(res.to_dict())
        except Exception as erro:
            respostas.append({
                "titulo": item.titulo,
                "erro": str(erro)
            })
    return respostas


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)