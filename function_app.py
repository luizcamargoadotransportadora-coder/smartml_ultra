"""
SmartML Ultra v100.2 - Ponto de Entrada para Google Cloud Functions
Conecta as requisições HTTP do Google Sheets / AppSheet ao motor matemático.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import functions_framework

# Garante a resolução correta dos módulos locais
RAIZ = Path(__file__).resolve().parent
SRC = RAIZ / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from config_loader import carregar_config
import motor

# Carrega a configuração em memória (execução rápida e sem custo de recarregamento)
try:
    cfg = carregar_config()
except Exception as e:
    cfg = None
    print(f"[ERRO] Falha ao carregar configuracao: {e}")


@functions_framework.http
def calcular_smartml(request):
    """
    Função HTTP executada na nuvem pelo Google Cloud Functions.
    Aceita requisições POST com payload JSON.
    """
    global cfg
    if cfg is None:
        cfg = carregar_config()

    # Tratamento de CORS para permitir chamadas de qualquer origem (AppSheet/Web)
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
        return ("", 204, headers)

    headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json"
    }

    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return (json.dumps({"erro": "Corpo da requisicao precisa ser um JSON valido."}), 400, headers)

        titulo = request_json.get("titulo")
        custo = request_json.get("custo")

        if not titulo or custo is None:
            return (json.dumps({"erro": "Campos 'titulo' e 'custo' sao obrigatorios."}), 422, headers)

        try:
            custo_float = float(custo)
            if custo_float <= 0:
                raise ValueError()
        except ValueError:
            return (json.dumps({"erro": "O campo 'custo' deve ser um numero maior que zero."}), 422, headers)

        moeda = str(request_json.get("moeda", "USD")).upper()
        categoria = request_json.get("categoria")
        peso_kg = float(request_json.get("peso_kg", 0.5))
        comprimento_cm = float(request_json.get("comprimento_cm", 20.0))
        largura_cm = float(request_json.get("largura_cm", 15.0))
        altura_cm = float(request_json.get("altura_cm", 10.0))
        estrategia = str(request_json.get("estrategia", "equilibrado"))

        # Executa o cálculo do motor
        resultado = motor.processar(
            cfg=cfg,
            titulo=titulo,
            custo=custo_float,
            moeda=moeda,
            categoria=categoria,
            peso_kg=peso_kg,
            comprimento_cm=comprimento_cm,
            largura_cm=largura_cm,
            altura_cm=altura_cm,
            estrategia=estrategia
        )

        return (json.dumps(resultado.to_dict()), 200, headers)

    except Exception as err:
        return (json.dumps({"erro": f"Erro interno de execucao: {str(err)}"}), 500, headers)