import pytest
from src.frete import criar_calculadora


@pytest.fixture(scope="module")
def calc():
    return criar_calculadora()


@pytest.fixture(scope="module")
def r_alto(calc):
    """Preco R$ 129,90 -> acima do limiar de R$ 79,00 -> frete gratis ativo."""
    return calc.calcular(peso_kg=1.2, comprimento_cm=30, largura_cm=25,
                         altura_cm=20, preco_venda_brl=129.9)


@pytest.fixture(scope="module")
def r_baixo(calc):
    """Preco R$ 39,90 -> abaixo do limiar -> sem frete gratis."""
    return calc.calcular(peso_kg=0.2, comprimento_cm=10, largura_cm=10,
                         altura_cm=5, preco_venda_brl=39.9)


# ---------------------------------------------------------------
# PESOS
# ---------------------------------------------------------------
def test_peso_real_preservado(r_alto):
    assert round(r_alto.peso_real_kg, 3) == 1.200


def test_peso_cubado_domina(r_alto):
    assert round(r_alto.peso_cubado_kg, 3) == 2.500
    assert round(r_alto.peso_faturado_kg, 3) == 2.580
    assert r_alto.peso_faturado_kg >= r_alto.peso_real_kg


def test_faixa_aplicada(r_alto):
    assert r_alto.faixa_aplicada == 5.0


# ---------------------------------------------------------------
# CUSTOS - ACIMA DO LIMIAR (frete gratis)
# ---------------------------------------------------------------
def test_custos_frete_gratis(r_alto):
    assert r_alto.frete_gratis_ativo is True
    assert round(r_alto.custo_tabela_brl, 2) == 24.90
    assert round(r_alto.custo_embalagem_brl, 2) == 1.20
    assert round(r_alto.custo_total_brl, 2) == 26.10


def test_rateio_frete_gratis(r_alto):
    assert r_alto.percentual_vendedor == 0.5
    assert round(r_alto.custo_vendedor_brl, 2) == 13.05


# ---------------------------------------------------------------
# CUSTOS - ABAIXO DO LIMIAR (sem frete gratis)
# ---------------------------------------------------------------
def test_abaixo_do_limiar(r_baixo):
    assert r_baixo.frete_gratis_ativo is False
    assert round(r_baixo.custo_vendedor_brl, 2) == round(r_baixo.custo_total_brl, 2)


def test_percentual_vendedor_integral(r_baixo):
    assert r_baixo.percentual_vendedor == 1.0


# ---------------------------------------------------------------
# COERENCIA CONTABIL
# ---------------------------------------------------------------
def test_composicao_do_total(r_alto):
    soma = r_alto.custo_tabela_brl + r_alto.custo_embalagem_brl
    assert round(soma, 2) == round(r_alto.custo_total_brl, 2)


def test_vendedor_nunca_excede_total(r_alto, r_baixo):
    for r in (r_alto, r_baixo):
        assert 0 <= round(r.custo_vendedor_brl, 2) <= round(r.custo_total_brl, 2)


def test_repasse_comprador_coerente(r_alto):
    repasse = round(r_alto.custo_total_brl - r_alto.custo_vendedor_brl, 2)
    assert repasse == 13.05


# ---------------------------------------------------------------
# AVISOS E INFRA
# ---------------------------------------------------------------
def test_avisos_gerados(r_alto):
    assert isinstance(r_alto.avisos, list)
    assert len(r_alto.avisos) >= 1


def test_fallback_sem_config():
    assert criar_calculadora(None) is not None


def test_entrada_invalida(calc):
    with pytest.raises((ValueError, AssertionError)):
        calc.calcular(peso_kg=-1, comprimento_cm=10, largura_cm=10,
                      altura_cm=5, preco_venda_brl=39.9)
