"""
SmartML Ultra v100.0 - Testes do motor de calculo e precificador integrado.
Rede de seguranca: valida classificacao, modalidades e precificacao reversa.
"""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.classificador import Faixa, analisar
from src.config_loader import carregar_config
from src.modalidades import Modalidade
from src.precificador import converter_para_brl, simular


@pytest.fixture(scope="module")
def cfg():
    return carregar_config()


# ---------- Deteccao de Categoria ----------
@pytest.mark.parametrize(
    "titulo, esperado",
    [
        ("iPhone 16 Pro Max 256GB Lacrado", "celular_premium"),
        ("Motorola Moto G84 5G 256GB", "celular_intermediario"),
        ("Fone AirPods Pro 2 Original", "eletronicos"),
        ("Notebook Dell Inspiron 15", "informatica"),
        ("Capa Silicone iPhone 15", "acessorios"),
        ("Cabo USB C para iPhone 15", "acessorios"),
        ("Pelicula de vidro Galaxy S24", "acessorios"),
        ("Panela de pressao 5 litros", "padrao"),
    ],
)
def test_deteccao_categoria(cfg, titulo, esperado):
    assert cfg.detectar_categoria(titulo) == esperado


def test_acessorio_vence_celular(cfg):
    """A prioridade garante que acessorio prevaleca sobre marcas de celular."""
    assert cfg.detectar_categoria("Capa iPhone 16 Pro Max") == "acessorios"


# ---------- Classificador ----------
def test_prejuizo_recebe_etiqueta_e_nao_erro(cfg):
    r = analisar(cfg, "iPhone 16 Pro Max", 5995.0, 7299.90)
    assert r.faixa == Faixa.PREJUIZO
    assert r.lucro_brl < 0


def test_lucro_e_margem_coerentes(cfg):
    r = analisar(cfg, "Notebook Dell Inspiron 15", 2450.0, 3757.90)
    assert r.lucro_brl > 0
    assert r.margem_pct == pytest.approx(
        r.lucro_brl / r.preco_venda_brl, abs=1e-6
    )


def test_nada_e_reprovado(cfg):
    """Todo produto recebe uma classificacao valida."""
    for titulo, custo, venda in [
        ("Pelicula Galaxy S24", 4.5, 39.90),
        ("iPhone 16 Pro Max", 5995.0, 9999.90),
        ("Produto qualquer", 10.0, 10.0),
    ]:
        r = analisar(cfg, titulo, custo, venda)
        assert isinstance(r.faixa, Faixa)


# ---------- Precificador Multi-Modalidade ----------
def test_empate_tem_lucro_quase_zero(cfg):
    sim = simular(cfg, "Notebook Dell Inspiron 15", 2450.0, "BRL")
    alvos_c = sim.modalidades[Modalidade.ML_CLASSICO].alvos
    alvos_p = sim.modalidades[Modalidade.ML_PREMIUM].alvos

    assert alvos_c["EMPATE"].lucro_brl == pytest.approx(0.0, abs=2.5)
    assert alvos_p["EMPATE"].lucro_brl == pytest.approx(0.0, abs=2.5)


def test_precos_sao_crescentes_em_todas_modalidades(cfg):
    sim = simular(cfg, "iPhone 16 Pro Max", 1100.0, "USD")
    ordem = ["EMPATE", "MINIMA", "BOA", "OBJETIVO"]

    for mod in (Modalidade.ML_CLASSICO, Modalidade.ML_PREMIUM):
        alvos = sim.modalidades[mod].alvos
        precos = [alvos[k].preco_sugerido_brl for k in ordem]
        assert precos == sorted(precos)


def test_premium_preco_maior_que_classico_para_mesma_margem(cfg):
    """Como a comissao Premium e maior, o preco sugerido deve ser maior."""
    sim = simular(cfg, "Motorola Moto G84 5G 256GB", 180.0, "USD")
    alvo_c = sim.modalidades[Modalidade.ML_CLASSICO].alvos["OBJETIVO"]
    alvo_p = sim.modalidades[Modalidade.ML_PREMIUM].alvos["OBJETIVO"]

    assert alvo_p.preco_sugerido_brl > alvo_c.preco_sugerido_brl


def test_cambio_aplica_spread(cfg):
    valor = 100.0
    cotacao = cfg.cambio.cotacoes_manuais["USD"]
    convertido = converter_para_brl(cfg, valor, "USD")
    assert convertido > valor * cotacao


def test_brl_nao_converte(cfg):
    assert converter_para_brl(cfg, 250.0, "BRL") == 250.0


def test_moeda_desconhecida_levanta_erro(cfg):
    with pytest.raises(ValueError):
        converter_para_brl(cfg, 100.0, "XYZ")