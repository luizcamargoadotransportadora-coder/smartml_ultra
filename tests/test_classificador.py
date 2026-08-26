"""Testes do classificador de oportunidades."""
from __future__ import annotations

import pytest

from src.classificador import SINAIS, Faixa, Resultado, analisar
from src.config_loader import carregar_config


@pytest.fixture(scope="module")
def cfg():
    return carregar_config()


def _preco_para_margem(cfg, cat, custo, margem_alvo):
    """Resolve o preco de venda que produz exatamente a margem desejada."""
    perf = cfg.perfil(cat)
    pct = perf.comissao_pct + cfg.custos.imposto_pct + cfg.custos.taxa_financeira_pct
    fixo = cfg.custos.total_fixo_brl
    # preco*(1 - pct - margem) = custo + fixo
    return (custo + fixo) / (1 - pct - margem_alvo)


# --------------------------------------------------------------
# estrutura
# --------------------------------------------------------------

def test_analisar_retorna_resultado(cfg):
    r = analisar(cfg, "iPhone 16 Pro Max 256GB Lacrado", 5995.0, 7899.90)
    assert isinstance(r, Resultado)
    assert r.titulo == "iPhone 16 Pro Max 256GB Lacrado"
    assert isinstance(r.faixa, Faixa)


def test_todas_as_faixas_tem_sinal():
    assert set(SINAIS) == set(Faixa)
    assert all(isinstance(s, str) and s for s in SINAIS.values())


def test_sinais_sao_unicos():
    assert len(set(SINAIS.values())) == len(SINAIS)


def test_propriedade_sinal_bate_com_a_faixa(cfg):
    r = analisar(cfg, "Capa Silicone iPhone 15", 18.0, 79.90)
    assert r.sinal == SINAIS[r.faixa]


def test_categoria_explicita_prevalece(cfg):
    cat = cfg.detectar_categoria("Capa Silicone iPhone 15")
    r = analisar(cfg, "Titulo Sem Nenhuma Pista", 50.0, 120.0, categoria=cat)
    assert r.categoria == cat


def test_categoria_detectada_automaticamente(cfg):
    titulo = "iPhone 16 Pro Max 256GB Lacrado"
    r = analisar(cfg, titulo, 5995.0, 7899.90)
    assert r.categoria == cfg.detectar_categoria(titulo)


def test_valores_monetarios_arredondados(cfg):
    r = analisar(cfg, "Motorola Moto G84 5G 256GB", 980.0, 1399.0)
    assert r.custo_total_brl == round(r.custo_total_brl, 2)
    assert r.lucro_brl == round(r.lucro_brl, 2)


# --------------------------------------------------------------
# aritmetica
# --------------------------------------------------------------

def test_lucro_e_preco_menos_custo_total(cfg):
    r = analisar(cfg, "Notebook Dell Inspiron 15 SSD 512GB", 2450.0, 3299.0)
    assert r.lucro_brl == pytest.approx(
        round(r.preco_venda_brl - r.custo_total_brl, 2), abs=0.01
    )


def test_margem_e_lucro_sobre_preco(cfg):
    r = analisar(cfg, "Notebook Dell Inspiron 15 SSD 512GB", 2450.0, 3299.0)
    assert r.margem_pct == pytest.approx(r.lucro_brl / r.preco_venda_brl, abs=1e-4)


def test_custo_total_supera_o_custo_do_produto(cfg):
    r = analisar(cfg, "Capa Silicone iPhone 15", 18.0, 79.90)
    assert r.custo_total_brl > r.custo_produto_brl


def test_preco_zero_nao_quebra(cfg):
    r = analisar(cfg, "Produto Fantasma", 10.0, 0.0)
    assert r.margem_pct == 0.0
    assert r.faixa is Faixa.PREJUIZO


def test_deducoes_crescem_com_o_preco(cfg):
    cat = cfg.detectar_categoria("Capa Silicone iPhone 15")
    a = analisar(cfg, "Capa Silicone iPhone 15", 18.0, 100.0, categoria=cat)
    b = analisar(cfg, "Capa Silicone iPhone 15", 18.0, 200.0, categoria=cat)
    assert (b.custo_total_brl - b.custo_produto_brl) > (
        a.custo_total_brl - a.custo_produto_brl
    )


# --------------------------------------------------------------
# faixas
# --------------------------------------------------------------

def test_prejuizo_quando_preco_abaixo_do_custo(cfg):
    r = analisar(cfg, "iPhone 16 Pro Max 256GB Lacrado", 5995.0, 3000.0)
    assert r.faixa is Faixa.PREJUIZO
    assert r.lucro_brl < 0


def test_margem_objetivo_gera_excelente(cfg):
    cat = cfg.detectar_categoria("iPhone 16 Pro Max 256GB Lacrado")
    perf = cfg.perfil(cat)
    preco = _preco_para_margem(cfg, cat, 5995.0, perf.margem_objetivo_pct + 0.02)
    r = analisar(cfg, "iPhone 16 Pro Max 256GB Lacrado", 5995.0, preco, categoria=cat)
    assert r.faixa is Faixa.EXCELENTE


def test_margem_intermediaria_gera_boa(cfg):
    cat = cfg.detectar_categoria("Motorola Moto G84 5G 256GB")
    perf = cfg.perfil(cat)
    limite = perf.margem_objetivo_pct * cfg.classificacao.fator_faixa_boa
    alvo = (limite + perf.margem_objetivo_pct) / 2
    preco = _preco_para_margem(cfg, cat, 980.0, alvo)
    r = analisar(cfg, "Motorola Moto G84 5G 256GB", 980.0, preco, categoria=cat)
    assert r.faixa is Faixa.BOA


def test_margem_critica_quando_abaixo_da_minima(cfg):
    cat = cfg.detectar_categoria("Motorola Moto G84 5G 256GB")
    perf = cfg.perfil(cat)
    preco = _preco_para_margem(cfg, cat, 980.0, perf.margem_minima_pct / 3)
    r = analisar(cfg, "Motorola Moto G84 5G 256GB", 980.0, preco, categoria=cat)
    assert r.faixa is Faixa.MARGEM_CRITICA
    assert r.lucro_brl > 0


def test_nada_e_reprovado_sempre_ha_faixa(cfg):
    casos = [
        ("iPhone 16 Pro Max 256GB Lacrado", 5995.0, 7899.90),
        ("Capa Silicone iPhone 15", 18.0, 79.90),
        ("Pelicula de vidro Galaxy S24", 4.50, 39.90),
        ("Panela de pressao 5 litros", 95.0, 149.90),
        ("Produto Ruim Demais", 500.0, 100.0),
        ("Titulo Estranho @@@ 123", 1.0, 1.0),
    ]
    for titulo, custo, venda in casos:
        r = analisar(cfg, titulo, custo, venda)
        assert r.faixa in set(Faixa)
        assert r.sinal in set(SINAIS.values())


def test_faixa_melhora_conforme_o_preco_sobe(cfg):
    cat = cfg.detectar_categoria("Motorola Moto G84 5G 256GB")
    ordem = [
        Faixa.PREJUIZO,
        Faixa.MARGEM_CRITICA,
        Faixa.MARGEM_BAIXA,
        Faixa.BOA,
        Faixa.EXCELENTE,
    ]
    anterior = -1
    for preco in (500.0, 1100.0, 1300.0, 1500.0, 2200.0, 4000.0):
        r = analisar(cfg, "Motorola Moto G84 5G 256GB", 980.0, preco, categoria=cat)
        atual = ordem.index(r.faixa)
        assert atual >= anterior
        anterior = atual


# --------------------------------------------------------------
# lucro minimo
# --------------------------------------------------------------

def test_lucro_alto_atende_o_minimo(cfg):
    r = analisar(cfg, "iPhone 16 Pro Max 256GB Lacrado", 5995.0, 9500.0)
    assert r.atende_lucro_minimo is True


def test_prejuizo_nao_atende_o_minimo(cfg):
    r = analisar(cfg, "iPhone 16 Pro Max 256GB Lacrado", 5995.0, 3000.0)
    assert r.atende_lucro_minimo is False


def test_flag_de_lucro_minimo_e_booleana(cfg):
    r = analisar(cfg, "Pelicula de vidro Galaxy S24", 4.50, 39.90)
    assert isinstance(r.atende_lucro_minimo, bool)
