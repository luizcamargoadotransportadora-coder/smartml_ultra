"""Testes do precificador reverso multi-modalidade."""
from __future__ import annotations

import pytest

from src.config_loader import carregar_config
from src.modalidades import Modalidade
from src.precificador import (
    Alvo,
    SimulacaoCompleta,
    arredondar,
    converter_para_brl,
    simular,
)

FAIXAS = ("EMPATE", "MINIMA", "BOA", "OBJETIVO")


@pytest.fixture(scope="module")
def cfg():
    return carregar_config()


# --------------------------------------------------------------
# converter_para_brl
# --------------------------------------------------------------

def test_moeda_base_nao_sofre_conversao(cfg):
    assert converter_para_brl(cfg, 250.0, cfg.cambio.moeda_base) == 250.0


def test_moeda_base_aceita_minusculo(cfg):
    base = cfg.cambio.moeda_base.lower()
    assert converter_para_brl(cfg, 99.0, base) == 99.0


def test_moeda_desconhecida_levanta_erro(cfg):
    with pytest.raises(ValueError):
        converter_para_brl(cfg, 100.0, "XYZ")


def test_conversao_aplica_spread(cfg):
    for moeda, cotacao in cfg.cambio.cotacoes_manuais.items():
        esperado = 100.0 * cotacao * (1 + cfg.cambio.spread_seguranca_pct)
        assert converter_para_brl(cfg, 100.0, moeda) == pytest.approx(esperado)


def test_conversao_e_proporcional(cfg):
    moeda = next(iter(cfg.cambio.cotacoes_manuais))
    um = converter_para_brl(cfg, 1.0, moeda)
    dez = converter_para_brl(cfg, 10.0, moeda)
    assert dez == pytest.approx(um * 10)


# --------------------------------------------------------------
# arredondar
# --------------------------------------------------------------

def test_arredondar_nunca_reduz_o_preco(cfg):
    for bruto in (10.10, 99.99, 100.00, 1234.56, 7.01):
        assert arredondar(cfg, bruto) >= bruto


def test_arredondar_respeita_final_psicologico(cfg):
    final = cfg.margem.arredondamento_preco
    for bruto in (10.10, 99.99, 250.34, 1780.02):
        centavos = round(arredondar(cfg, bruto) % 1, 2)
        assert centavos == pytest.approx(round(final % 1, 2), abs=0.011)


def test_arredondar_nao_infla_demais(cfg):
    for bruto in (10.10, 99.99, 250.34):
        assert arredondar(cfg, bruto) - bruto < 1.01


# --------------------------------------------------------------
# simular - estrutura
# --------------------------------------------------------------

def test_simular_retorna_estrutura_completa(cfg):
    sim = simular(cfg, "iPhone 16 Pro Max 256GB", 1100.0, "USD")
    assert isinstance(sim, SimulacaoCompleta)
    assert sim.moeda_origem == "USD"
    assert sim.custo_origem == 1100.0
    assert sim.custo_brl > 0


def test_simular_traz_as_duas_modalidades(cfg):
    sim = simular(cfg, "Capa Silicone iPhone 15", 18.0, "BRL")
    assert Modalidade.ML_CLASSICO in sim.modalidades
    assert Modalidade.ML_PREMIUM in sim.modalidades


def test_todas_as_faixas_presentes(cfg):
    sim = simular(cfg, "Motorola Moto G84 5G", 180.0, "USD")
    for mod in (Modalidade.ML_CLASSICO, Modalidade.ML_PREMIUM):
        alvos = sim.modalidades[mod].alvos
        assert set(alvos) == set(FAIXAS)
        assert all(isinstance(a, Alvo) for a in alvos.values())


def test_categoria_explicita_prevalece(cfg):
    cat = cfg.detectar_categoria("Capa Silicone iPhone 15")
    sim = simular(cfg, "Titulo Qualquer Sem Pista", 50.0, "BRL", categoria=cat)
    assert sim.categoria == cat


def test_resultado_de_frete_sempre_anexado(cfg):
    sim = simular(cfg, "Capa Silicone iPhone 15", 18.0, "BRL", peso_kg=0.1)
    for mod in sim.modalidades.values():
        for alvo in mod.alvos.values():
            assert alvo.resultado_frete is not None


# --------------------------------------------------------------
# simular - comportamento economico
# --------------------------------------------------------------

def test_precos_sobem_conforme_a_faixa(cfg):
    sim = simular(cfg, "iPhone 16 Pro Max 256GB", 1100.0, "USD")
    for mod in sim.modalidades.values():
        precos = [mod.alvos[f].preco_sugerido_brl for f in FAIXAS]
        assert precos == sorted(precos)


def test_lucros_sobem_conforme_a_faixa(cfg):
    sim = simular(cfg, "iPhone 16 Pro Max 256GB", 1100.0, "USD")
    for mod in sim.modalidades.values():
        lucros = [mod.alvos[f].lucro_brl for f in FAIXAS]
        assert lucros == sorted(lucros)


def test_empate_tem_lucro_proximo_de_zero(cfg):
    sim = simular(cfg, "Motorola Moto G84 5G", 180.0, "USD")
    for mod in sim.modalidades.values():
        lucro = mod.alvos["EMPATE"].lucro_brl
        assert -1.0 <= lucro <= 5.0


def test_premium_cobra_mais_caro_que_classico(cfg):
    sim = simular(cfg, "iPhone 16 Pro Max 256GB", 1100.0, "USD")
    c = sim.modalidades[Modalidade.ML_CLASSICO]
    p = sim.modalidades[Modalidade.ML_PREMIUM]
    if p.comissao_pct > c.comissao_pct:
        for f in FAIXAS:
            assert p.alvos[f].preco_sugerido_brl >= c.alvos[f].preco_sugerido_brl


def test_preco_sempre_supera_o_custo(cfg):
    sim = simular(cfg, "iPhone 16 Pro Max 256GB", 1100.0, "USD")
    for mod in sim.modalidades.values():
        for alvo in mod.alvos.values():
            assert alvo.preco_sugerido_brl > sim.custo_brl


def test_custo_maior_gera_preco_maior(cfg):
    barato = simular(cfg, "Capa Silicone iPhone 15", 18.0, "BRL")
    caro = simular(cfg, "Capa Silicone iPhone 15", 180.0, "BRL")
    a = barato.modalidades[Modalidade.ML_CLASSICO].alvos["OBJETIVO"]
    b = caro.modalidades[Modalidade.ML_CLASSICO].alvos["OBJETIVO"]
    assert b.preco_sugerido_brl > a.preco_sugerido_brl


def test_pacote_pesado_encarece_o_preco(cfg):
    leve = simular(cfg, "Capa Silicone iPhone 15", 100.0, "BRL", peso_kg=0.1)
    pesado = simular(cfg, "Capa Silicone iPhone 15", 100.0, "BRL", peso_kg=9.0)
    a = leve.modalidades[Modalidade.ML_CLASSICO].alvos["OBJETIVO"]
    b = pesado.modalidades[Modalidade.ML_CLASSICO].alvos["OBJETIVO"]
    assert b.preco_sugerido_brl >= a.preco_sugerido_brl


def test_margem_pct_bate_com_a_configuracao(cfg):
    sim = simular(cfg, "iPhone 16 Pro Max 256GB", 1100.0, "USD")
    perf = cfg.perfil(sim.categoria)
    alvos = sim.modalidades[Modalidade.ML_CLASSICO].alvos
    assert alvos["EMPATE"].margem_pct == 0.0
    assert alvos["MINIMA"].margem_pct == pytest.approx(perf.margem_minima_pct)
    assert alvos["OBJETIVO"].margem_pct == pytest.approx(perf.margem_objetivo_pct)


def test_valores_sao_arredondados_em_centavos(cfg):
    sim = simular(cfg, "Motorola Moto G84 5G", 180.0, "USD")
    for mod in sim.modalidades.values():
        for alvo in mod.alvos.values():
            assert alvo.preco_sugerido_brl == round(alvo.preco_sugerido_brl, 2)
            assert alvo.lucro_brl == round(alvo.lucro_brl, 2)
