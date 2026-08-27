import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from config_loader import carregar_config
import motor


@pytest.fixture(scope="module")
def cfg():
    return carregar_config()


@pytest.fixture(scope="module")
def res(cfg):
    return motor.processar(cfg, titulo="Fone Bluetooth JBL", custo=100.0, moeda="USD", categoria="eletronico", peso_kg=0.4)


def test_titulo_preservado(res):
    assert res.titulo == "Fone Bluetooth JBL"


def test_custo_convertido(res):
    assert res.custo_brl > 100.0


def test_gera_opcoes(res):
    assert len(res.opcoes) == 8


def test_modalidade_e_rotulo_curto(res):
    for o in res.opcoes:
        assert o.modalidade in ("Classico", "Premium")


def test_frete_positivo(res):
    assert all(o.frete_brl > 0 for o in res.opcoes)


def test_recomendada_existe(res):
    assert res.recomendada in res.opcoes


def test_preco_cobre_custo(res):
    for o in res.opcoes:
        assert o.preco_sugerido_brl > res.custo_brl


def test_lucro_nao_negativo(res):
    assert all(o.lucro_brl >= 0 for o in res.opcoes)


def test_classificacao_preenchida(res):
    assert all(isinstance(o.classificacao, str) and o.classificacao for o in res.opcoes)


def test_avisos_sem_duplicata(res):
    assert len(res.avisos) == len(set(res.avisos))


def test_recomendada_nao_e_critica(res):
    rec = res.recomendada
    assert rec is not None
    assert "CRITICA" not in str(rec.classificacao).upper(), f"Sistema recomendou uma opcao critica: {rec.classificacao}"


def _mostra_recomendada(res):
    print("\nRECOMENDADA:", res.recomendada)
    for o in res.opcoes:
        print(" -", o.modalidade, o.preco_sugerido_brl, o.lucro_brl, o.classificacao)
