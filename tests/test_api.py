"""
SmartML Ultra v100.1 - Testes Unitários da API HTTP (FastAPI)
Valida os endpoints /, /analisar e /analisar-lote.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from main import app

client = TestClient(app)


def test_health_check():
    """Valida se o endpoint raiz responde com status 200 e dados do sistema."""
    response = client.get("/")
    assert response.status_code == 200
    dados = response.json()
    assert dados["status"] == "online"
    assert dados["sistema"] == "SmartML Ultra"
    assert dados["versao"] == "100.1"


def test_analisar_produto_valido():
    """Valida o cálculo completo de um produto via endpoint POST /analisar."""
    payload = {
        "titulo": "iPhone 16 Pro Max 256GB Lacrado",
        "custo": 1100.0,
        "moeda": "USD",
        "categoria": "celular_premium",
        "peso_kg": 0.6,
        "comprimento_cm": 20.0,
        "largura_cm": 15.0,
        "altura_cm": 10.0,
        "estrategia": "equilibrado"
    }
    response = client.post("/analisar", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["titulo"] == payload["titulo"]
    assert res["custo_brl"] > 1100.0
    assert len(res["opcoes"]) == 8
    assert res["recomendada"] is not None
    assert "classificacao" in res["recomendada"]


def test_analisar_produto_custo_invalido():
    """Garante que a API rejeita requisições com valores monetários zerados ou negativos."""
    payload = {
        "titulo": "Produto Invalido",
        "custo": 0.0,
        "moeda": "USD"
    }
    response = client.post("/analisar", json=payload)
    assert response.status_code == 422


def test_analisar_lote():
    """Valida o endpoint POST /analisar-lote processando múltiplos itens."""
    payload = {
        "produtos": [
            {
                "titulo": "iPhone 16 Pro Max 256GB",
                "custo": 1100.0,
                "moeda": "USD",
                "peso_kg": 0.6
            },
            {
                "titulo": "Capa Silicone iPhone 15",
                "custo": 18.0,
                "moeda": "BRL",
                "peso_kg": 0.1
            }
        ]
    }
    response = client.post("/analisar-lote", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert isinstance(res, list)
    assert len(res) == 2
    assert res[0]["titulo"] == "iPhone 16 Pro Max 256GB"
    assert res[1]["titulo"] == "Capa Silicone iPhone 15"