"""
SmartML Ultra v100.0 - Precificador Reverso Multi-Modalidade.
Integra calculo logistico real (peso/cubagem) e compara Classico vs Premium.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from src.config_loader import Configuracao, carregar_config
from src.frete import CalculadoraFrete, ResultadoFrete, criar_calculadora
from src.modalidades import Modalidade, comissao_de


@dataclass
class Alvo:
    rotulo: str
    margem_pct: float
    preco_sugerido_brl: float
    lucro_brl: float
    resultado_frete: Optional[ResultadoFrete] = None


@dataclass
class SimulacaoModalidade:
    modalidade: Modalidade
    comissao_pct: float
    alvos: Dict[str, Alvo]


@dataclass
class SimulacaoCompleta:
    titulo: str
    categoria: str
    moeda_origem: str
    custo_origem: float
    custo_brl: float
    modalidades: Dict[Modalidade, SimulacaoModalidade]


def converter_para_brl(cfg: Configuracao, valor: float, moeda: str) -> float:
    """Converte o custo para reais aplicando spread de seguranca."""
    moeda = moeda.upper()
    if moeda == cfg.cambio.moeda_base:
        return valor

    cotacao = cfg.cambio.cotacoes_manuais.get(moeda)
    if cotacao is None:
        raise ValueError(f"Sem cotacao cadastrada para {moeda}")

    bruto = valor * cotacao
    return bruto * (1 + cfg.cambio.spread_seguranca_pct)


def arredondar(cfg: Configuracao, preco: float) -> float:
    """Sobe o preco para o final psicologico definido no YAML."""
    final = cfg.margem.arredondamento_preco
    base = int(preco)
    candidato = base + final
    if candidato < preco:
        candidato = base + 1 + final
    return round(candidato, 2)


def _resolver_preco_com_frete(
    cfg: Configuracao,
    calc_frete: CalculadoraFrete,
    custo_produto_brl: float,
    comissao_pct: float,
    margem_desejada: float,
    peso_kg: float,
    comprimento_cm: float,
    largura_cm: float,
    altura_cm: float,
) -> tuple[float, float, ResultadoFrete]:
    pct_impostos_taxas = cfg.custos.imposto_pct + cfg.custos.taxa_financeira_pct
    pct_total = comissao_pct + pct_impostos_taxas
    divisor = 1.0 - pct_total - margem_desejada

    if divisor <= 0:
        raise ValueError("Soma de comissao, taxas e margem >= 100%.")

    preco_estimado = custo_produto_brl / divisor
    resultado_frete = None

    for _ in range(8):
        resultado_frete = calc_frete.calcular(
            peso_kg=peso_kg,
            comprimento_cm=comprimento_cm,
            largura_cm=largura_cm,
            altura_cm=altura_cm,
            preco_venda_brl=preco_estimado,
        )
        custo_vendedor = resultado_frete.custo_vendedor_brl
        novo_preco = (custo_produto_brl + custo_vendedor) / divisor
        if abs(novo_preco - preco_estimado) < 0.01:
            break
        preco_estimado = novo_preco

    preco_final = arredondar(cfg, preco_estimado)
    resultado_frete = calc_frete.calcular(
        peso_kg=peso_kg,
        comprimento_cm=comprimento_cm,
        largura_cm=largura_cm,
        altura_cm=altura_cm,
        preco_venda_brl=preco_final,
    )
    deducoes = preco_final * pct_total
    lucro = preco_final - custo_produto_brl - resultado_frete.custo_vendedor_brl - deducoes

    return preco_final, round(lucro, 2), resultado_frete


def simular(
    cfg: Configuracao,
    titulo: str,
    custo: float,
    moeda: str = "BRL",
    categoria: Optional[str] = None,
    peso_kg: float = 0.5,
    comprimento_cm: float = 20.0,
    largura_cm: float = 15.0,
    altura_cm: float = 10.0,
) -> SimulacaoCompleta:
    cat = categoria or cfg.detectar_categoria(titulo)
    perf = cfg.perfil(cat)
    custo_brl = converter_para_brl(cfg, custo, moeda)
    calc_frete = criar_calculadora()

    faixas = {
        "EMPATE": 0.0,
        "MINIMA": perf.margem_minima_pct,
        "BOA": perf.margem_objetivo_pct * cfg.classificacao.fator_faixa_boa,
        "OBJETIVO": perf.margem_objetivo_pct,
    }

    modalidades_simuladas: Dict[Modalidade, SimulacaoModalidade] = {}

    for mod in (Modalidade.ML_CLASSICO, Modalidade.ML_PREMIUM):
        comissao = comissao_de(cat, mod)
        alvos: Dict[str, Alvo] = {}

        for rotulo, margem in faixas.items():
            preco, lucro, res_frete = _resolver_preco_com_frete(
                cfg=cfg,
                calc_frete=calc_frete,
                custo_produto_brl=custo_brl,
                comissao_pct=comissao,
                margem_desejada=margem,
                peso_kg=peso_kg,
                comprimento_cm=comprimento_cm,
                largura_cm=largura_cm,
                altura_cm=altura_cm,
            )
            alvos[rotulo] = Alvo(
                rotulo=rotulo,
                margem_pct=margem,
                preco_sugerido_brl=preco,
                lucro_brl=lucro,
                resultado_frete=res_frete,
            )

        modalidades_simuladas[mod] = SimulacaoModalidade(
            modalidade=mod,
            comissao_pct=comissao,
            alvos=alvos,
        )

    return SimulacaoCompleta(
        titulo=titulo,
        categoria=cat,
        moeda_origem=moeda.upper(),
        custo_origem=custo,
        custo_brl=round(custo_brl, 2),
        modalidades=modalidades_simuladas,
    )


def imprimir_comparativo(cfg: Configuracao, sim: SimulacaoCompleta) -> None:
    perf = cfg.perfil(sim.categoria)
    print("=" * 76)
    print(f"  PRODUTO: {sim.titulo[:60]}")
    print("=" * 76)
    print(f"  Categoria : {sim.categoria:<20} Custo: {sim.moeda_origem} {sim.custo_origem:,.2f} (R$ {sim.custo_brl:,.2f})")
    print(f"  Piso R$   : R$ {perf.lucro_minimo_brl:,.2f} lucro minimo")
    print("-" * 76)
    print(f"  {'FAIXA':<10} | {'CLASSICO (Vender / Lucro)':<28} | {'PREMIUM (Vender / Lucro)':<28}")
    print("  " + "-" * 72)

    alvos_c = sim.modalidades[Modalidade.ML_CLASSICO].alvos
    alvos_p = sim.modalidades[Modalidade.ML_PREMIUM].alvos

    for chave in ("EMPATE", "MINIMA", "BOA", "OBJETIVO"):
        ac = alvos_c[chave]
        ap = alvos_p[chave]
        txt_c = f"R$ {ac.preco_sugerido_brl:>8,.2f} -> R$ {ac.lucro_brl:>7,.2f}"
        txt_p = f"R$ {ap.preco_sugerido_brl:>8,.2f} -> R$ {ap.lucro_brl:>7,.2f}"
        print(f"  {chave:<10} | {txt_c:<28} | {txt_p:<28}")

    print("=" * 76)
    print()


if __name__ == "__main__":
    cfg = carregar_config()
    casos = [
        ("iPhone 16 Pro Max 256GB Lacrado", 1100.00, "USD", 0.6, 20.0, 15.0, 10.0),
        ("Motorola Moto G84 5G 256GB", 180.00, "USD", 0.6, 20.0, 15.0, 10.0),
        ("Capa Silicone iPhone 15", 18.00, "BRL", 0.1, 20.0, 15.0, 3.0),
    ]
    for titulo, custo, moeda, p, c, l, a in casos:
        imprimir_comparativo(
            cfg,
            simular(cfg, titulo, custo, moeda, peso_kg=p, comprimento_cm=c, largura_cm=l, altura_cm=a),
        )