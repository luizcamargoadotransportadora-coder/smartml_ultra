"""
SmartML Ultra v100.0 - Classificador de oportunidades.
Nada e reprovado: tudo recebe uma etiqueta de viabilidade.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.config_loader import Configuracao, carregar_config


class Faixa(str, Enum):
    EXCELENTE = "EXCELENTE"
    BOA = "BOA"
    MARGEM_BAIXA = "MARGEM_BAIXA"
    MARGEM_CRITICA = "MARGEM_CRITICA"
    PREJUIZO = "PREJUIZO"


SINAIS = {
    Faixa.EXCELENTE: "[A]",
    Faixa.BOA: "[B]",
    Faixa.MARGEM_BAIXA: "[C]",
    Faixa.MARGEM_CRITICA: "[D]",
    Faixa.PREJUIZO: "[E]",
}


@dataclass
class Resultado:
    titulo: str
    categoria: str
    custo_produto_brl: float
    custo_total_brl: float
    preco_venda_brl: float
    lucro_brl: float
    margem_pct: float
    faixa: Faixa
    atende_lucro_minimo: bool

    @property
    def sinal(self) -> str:
        return SINAIS[self.faixa]


def analisar(
    cfg: Configuracao,
    titulo: str,
    custo_produto_brl: float,
    preco_venda_brl: float,
    categoria: Optional[str] = None,
) -> Resultado:
    """Calcula lucro, margem e devolve a etiqueta da oportunidade."""
    cat = categoria or cfg.detectar_categoria(titulo)
    perf = cfg.perfil(cat)

    pct_sobre_venda = (
        perf.comissao_pct
        + cfg.custos.imposto_pct
        + cfg.custos.taxa_financeira_pct
    )

    deducoes = preco_venda_brl * pct_sobre_venda
    custo_total = custo_produto_brl + cfg.custos.total_fixo_brl + deducoes
    lucro = preco_venda_brl - custo_total
    margem = lucro / preco_venda_brl if preco_venda_brl else 0.0

    limite_boa = perf.margem_objetivo_pct * cfg.classificacao.fator_faixa_boa

    if lucro <= 0:
        faixa = Faixa.PREJUIZO
    elif margem >= perf.margem_objetivo_pct:
        faixa = Faixa.EXCELENTE
    elif margem >= limite_boa:
        faixa = Faixa.BOA
    elif margem >= perf.margem_minima_pct:
        faixa = Faixa.MARGEM_BAIXA
    else:
        faixa = Faixa.MARGEM_CRITICA

    return Resultado(
        titulo=titulo,
        categoria=cat,
        custo_produto_brl=custo_produto_brl,
        custo_total_brl=round(custo_total, 2),
        preco_venda_brl=preco_venda_brl,
        lucro_brl=round(lucro, 2),
        margem_pct=margem,
        faixa=faixa,
        atende_lucro_minimo=lucro >= perf.lucro_minimo_brl,
    )


if __name__ == "__main__":
    cfg = carregar_config()

    casos = [
        ("iPhone 16 Pro Max 256GB Lacrado", 5995.00, 7899.90),
        ("iPhone 16 Pro Max 256GB Lacrado", 5995.00, 7299.90),
        ("Motorola Moto G84 5G 256GB", 980.00, 1399.00),
        ("Fone AirPods Pro 2 Original", 890.00, 1249.00),
        ("Capa Silicone iPhone 15", 18.00, 79.90),
        ("Pelicula de vidro Galaxy S24", 4.50, 39.90),
        ("Notebook Dell Inspiron 15 SSD 512GB", 2450.00, 3299.00),
        ("Panela de pressao 5 litros", 95.00, 149.90),
    ]

    resultados = [analisar(cfg, t, c, v) for t, c, v in casos]
    resultados.sort(key=lambda r: r.lucro_brl, reverse=True)

    print("=" * 82)
    print("  SMARTML ULTRA - ANALISE DE OPORTUNIDADES")
    print("=" * 82)
    print(
        f"  {'':<5}{'PRODUTO':<34}{'CATEGORIA':<22}"
        f"{'LUCRO':>10}{'MARGEM':>8}"
    )
    print("  " + "-" * 78)

    for r in resultados:
        alerta = " (!)" if not r.atende_lucro_minimo else ""
        print(
            f"  {r.sinal:<5}{r.titulo[:32]:<34}{r.categoria:<22}"
            f"{r.lucro_brl:>10.2f}{r.margem_pct:>7.1%}{alerta}"
        )

    print("=" * 82)