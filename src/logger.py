"""
SmartML Ultra v100.0 - Configuracao central de logging.
Grava em arquivo rotativo e mostra no terminal.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
PASTA_LOGS = RAIZ / "logs"

FORMATO_ARQUIVO = (
    "%(asctime)s | %(levelname)-8s | %(name)-18s | %(message)s"
)
FORMATO_TELA = "%(levelname)-8s | %(message)s"

MAX_BYTES = 2 * 1024 * 1024
BACKUPS = 5


def obter_logger(
    nome: str = "smartml",
    nivel: int = logging.INFO,
    arquivo: str = "smartml.log",
) -> logging.Logger:
    """Cria (ou reaproveita) um logger com saida dupla."""
    log = logging.getLogger(nome)

    if log.handlers:
        return log

    log.setLevel(logging.DEBUG)
    log.propagate = False

    PASTA_LOGS.mkdir(parents=True, exist_ok=True)

    h_arquivo = RotatingFileHandler(
        PASTA_LOGS / arquivo,
        maxBytes=MAX_BYTES,
        backupCount=BACKUPS,
        encoding="utf-8",
    )
    h_arquivo.setLevel(logging.DEBUG)
    h_arquivo.setFormatter(logging.Formatter(FORMATO_ARQUIVO))

    h_tela = logging.StreamHandler(sys.stdout)
    h_tela.setLevel(nivel)
    h_tela.setFormatter(logging.Formatter(FORMATO_TELA))

    log.addHandler(h_arquivo)
    log.addHandler(h_tela)

    return log


if __name__ == "__main__":
    log = obter_logger("smartml.teste")

    log.debug("Mensagem DEBUG - so vai para o arquivo")
    log.info("Mensagem INFO - aparece nos dois")
    log.warning("Mensagem WARNING - algo merece atencao")
    log.error("Mensagem ERROR - deu problema")

    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("Erro capturado com rastreamento completo")

    destino = PASTA_LOGS / "smartml.log"
    print()
    print("=" * 66)
    print(f"  Log gravado em: {destino}")
    print(f"  Arquivo existe: {destino.exists()}")
    if destino.exists():
        print(f"  Tamanho: {destino.stat().st_size} bytes")
    print("=" * 66)
