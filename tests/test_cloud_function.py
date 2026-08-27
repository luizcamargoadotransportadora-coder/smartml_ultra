"""
SmartML Ultra v100.2 - Testes da Cloud Function
Valida se a função calcular_smartml responde com o padrão exigido pelo Google Cloud.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from function_app import calcular_smartml


def test_cloud_function_options_cors():
    """Valida pre-flight request CORS (OPTIONS)."""
    req = MagicMock()
    req.method = "OPTIONS"
    body, status, headers = calcular_smartml(req)
    assert status == 204
    assert headers["Access-Control-Allow-Origin"] == "*"


def test_cloud_function_calculo_sucesso():
    """Valida cálculo com sucesso via Cloud Function."""
    req = MagicMock()
    req.method = "POST"
    req.get_json.return_value = {
        "titulo": "iPhone 16 Pro Max 256GB Lacrado",
        "custo": 1100.0,
        "moeda": "USD",
        "peso_kg": 0.6
    }
    body, status, headers = calcular_smartml(req)
    assert status == 200
    dados = json.loads(body)
    assert dados["titulo"] == "iPhone 16 Pro Max 256GB Lacrado"
    assert dados["custo_brl"] > 1100.0
    assert len(dados["opcoes"]) == 8


def test_cloud_function_sem_campos_obrigatorios():
    """Valida erro 422 quando falta titulo ou custo."""
    req = MagicMock()
    req.method = "POST"
    req.get_json.return_value = {"titulo": "Sem Custo"}
    body, status, headers = calcular_smartml(req)
    assert status == 422
    dados = json.loads(body)
    assert "erro" in dados