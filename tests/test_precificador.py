"""Testes do módulo precificador — SmartML Ultra v100.0"""
import importlib
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
for p in (RAIZ, RAIZ / "src", RAIZ / "app"):
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

CANDIDATOS = ("", "src.", "app.", "smartml.", "smartml_ultra.", "core.")


def _importar(nome_modulo, *atributos):
    erros = []
    for prefixo in CANDIDATOS:
        for sufixo in ("", f".{nome_modulo}", ".loader", ".main"):
            caminho = f"{prefixo}{nome_modulo}{sufixo}"
            try:
                mod = importlib.import_module(caminho)
            except Exception as e:
                erros.append(f"{caminho}: {e}")
                continue
            if all(hasattr(mod, a) for a in atributos):
                return mod
            erros.append(f"{caminho}: faltam atributos")
    raise ImportError(
        f"Nao achei '{nome_modulo}' com {atributos}.\nTentativas:\n  "
        + "\n  ".join(erros)
    )


_cfg_mod = _importar("config_loader", "carregar_config")
carregar_config = _cfg_mod.carregar_config

_pre = _importar("precificador", "simular", "arredondar", "Modalidade")
simular = _pre.simular
arredondar = _pre.arredondar
Modalidade = _pre.Modalidade
_resolver_preco_com_frete = getattr(_pre, "_resolver_preco_com_frete", None)

_frete = _importar("frete", "criar_calculadora")
criar_calculadora = _frete.criar_calculadora


FAIXAS = ("EMPATE", "MINIMA", "BOA", "OBJETIVO")

_NOMES_FINAL = ("arredondamento_preco", "final_psicologico", "final",
                "terminacao", "arredondamento_final", "centavos_finais")


def _final_psicologico(cfg):
    """Descobre o campo do final psicologico, tenha ele o nome que tiver."""
    for bloco in (getattr(cfg, "margem", None),
                  getattr(cfg, "precificacao", None),
                  cfg):
        if bloco is None:
            continue
        # objetos com atributos
        for nome in _NOMES_FINAL:
            if hasattr(bloco, nome):
                return float(getattr(bloco, nome))
        # dicts
        if isinstance(bloco, dict):
            for nome in _NOMES_FINAL:
                if nome in bloco:
                    return float(bloco[nome])
    pytest.skip("Campo de final psicologico nao encontrado na config")


@pytest.fixture(scope="module")
def cfg():
    return carregar_config()


@pytest.fixture(scope="module")
def sim_celular(cfg):
    return simular(cfg, "iPhone 16 Pro Max 256GB Lacrado", 1100.00, "USD",
                   peso_kg=0.6, comprimento_cm=20.0, largura_cm=15.0,
                   altura_cm=10.0)


@pytest.fixture(scope="module")
def sim_acessorio(cfg):
    return simular(cfg, "Capa Silicone iPhone 15", 18.00, "BRL",
                   peso_kg=0.1, comprimento_cm=20.0, largura_cm=15.0,
                   altura_cm=3.0)


# ---------- 1. Estrutura do retorno ----------

def test_simulacao_tem_as_duas_modalidades(sim_celular):
    assert Modalidade.ML_CLASSICO in sim_celular.modalidades
    assert Modalidade.ML_PREMIUM in sim_celular.modalidades


def test_cada_modalidade_tem_as_quatro_faixas(sim_celular):
    for mod in (Modalidade.ML_CLASSICO, Modalidade.ML_PREMIUM):
        assert set(sim_celular.modalidades[mod].alvos.keys()) == set(FAIXAS)


def test_conversao_de_moeda_aplicada(sim_celular):
    assert sim_celular.moeda_origem == "USD"
    assert sim_celular.custo_brl > sim_celular.custo_origem


def test_custo_brl_nao_converte_quando_ja_e_brl(sim_acessorio):
    assert sim_acessorio.custo_brl == pytest.approx(18.00, abs=0.01)


# ---------- 2. Monotonicidade ----------

def test_precos_crescem_com_a_margem(sim_celular):
    for mod in (Modalidade.ML_CLASSICO, Modalidade.ML_PREMIUM):
        alvos = sim_celular.modalidades[mod].alvos
        precos = [alvos[f].preco_sugerido_brl for f in FAIXAS]
        assert precos == sorted(precos), f"{mod}: {precos}"


def test_lucros_crescem_com_a_margem(sim_celular):
    for mod in (Modalidade.ML_CLASSICO, Modalidade.ML_PREMIUM):
        alvos = sim_celular.modalidades[mod].alvos
        lucros = [alvos[f].lucro_brl for f in FAIXAS]
        assert lucros == sorted(lucros), f"{mod}: {lucros}"


def test_premium_custa_mais_que_classico(sim_celular):
    c = sim_celular.modalidades[Modalidade.ML_CLASSICO]
    p = sim_celular.modalidades[Modalidade.ML_PREMIUM]
    assert p.comissao_pct > c.comissao_pct
    for f in FAIXAS:
        assert p.alvos[f].preco_sugerido_brl >= c.alvos[f].preco_sugerido_brl


# ---------- 3. Coerencia financeira ----------

def test_empate_tem_lucro_proximo_de_zero(sim_celular):
    for mod in (Modalidade.ML_CLASSICO, Modalidade.ML_PREMIUM):
        assert sim_celular.modalidades[mod].alvos["EMPATE"].lucro_brl >= -0.5


def test_lucro_bate_com_a_margem_desejada(sim_celular):
    for mod in (Modalidade.ML_CLASSICO, Modalidade.ML_PREMIUM):
        for f in ("MINIMA", "BOA", "OBJETIVO"):
            a = sim_celular.modalidades[mod].alvos[f]
            esperado = a.preco_sugerido_brl * a.margem_pct
            assert a.lucro_brl >= esperado - 1.0, (
                f"{mod}/{f}: {a.lucro_brl:.2f} < {esperado:.2f}")


def test_preco_sempre_maior_que_custo(sim_celular):
    for mod in (Modalidade.ML_CLASSICO, Modalidade.ML_PREMIUM):
        for f in FAIXAS:
            assert (sim_celular.modalidades[mod].alvos[f].preco_sugerido_brl
                    > sim_celular.custo_brl)


# ---------- 4. Arredondamento psicologico ----------

def test_arredondar_nunca_desce(cfg):
    for bruto in (10.00, 10.01, 47.35, 78.40, 99.99, 1234.56):
        assert arredondar(cfg, bruto) >= bruto


def test_arredondar_respeita_o_final(cfg):
    final = _final_psicologico(cfg)
    for bruto in (10.00, 47.35, 78.40, 1234.56):
        assert round(arredondar(cfg, bruto) % 1, 2) == pytest.approx(
            round(final % 1, 2), abs=0.001)


def test_precos_finais_terminam_no_final_psicologico(cfg, sim_celular):
    final = _final_psicologico(cfg)
    for mod in (Modalidade.ML_CLASSICO, Modalidade.ML_PREMIUM):
        for f in FAIXAS:
            preco = sim_celular.modalidades[mod].alvos[f].preco_sugerido_brl
            assert round(preco % 1, 2) == pytest.approx(
                round(final % 1, 2), abs=0.001)


# ---------- 5. Loop iterativo do frete ----------

@pytest.mark.skipif(_resolver_preco_com_frete is None,
                    reason="_resolver_preco_com_frete nao exposto")
def test_divisor_invalido_levanta_valueerror(cfg):
    with pytest.raises(ValueError):
        _resolver_preco_com_frete(
            cfg=cfg, calc_frete=criar_calculadora(),
            custo_produto_brl=100.0, comissao_pct=0.90,
            margem_desejada=0.50, peso_kg=0.5,
            comprimento_cm=20.0, largura_cm=15.0, altura_cm=10.0)


@pytest.mark.skipif(_resolver_preco_com_frete is None,
                    reason="_resolver_preco_com_frete nao exposto")
def test_resolver_converge_e_devolve_tripla(cfg):
    preco, lucro, res = _resolver_preco_com_frete(
        cfg=cfg, calc_frete=criar_calculadora(),
        custo_produto_brl=100.0, comissao_pct=0.14,
        margem_desejada=0.15, peso_kg=0.5,
        comprimento_cm=20.0, largura_cm=15.0, altura_cm=10.0)
    assert preco > 100.0
    assert lucro > 0
    assert res is not None


def test_frete_recalculado_no_preco_final(sim_celular):
    for mod in (Modalidade.ML_CLASSICO, Modalidade.ML_PREMIUM):
        for f in FAIXAS:
            assert sim_celular.modalidades[mod].alvos[f].resultado_frete is not None


def test_acessorio_barato_tem_preco_acima_do_custo(sim_acessorio):
    alvos = sim_acessorio.modalidades[Modalidade.ML_CLASSICO].alvos
    for f in FAIXAS:
        assert alvos[f].preco_sugerido_brl > sim_acessorio.custo_brl


# ---------- 6. Determinismo ----------

def test_simular_e_deterministico(cfg):
    a = simular(cfg, "Motorola Moto G84 5G 256GB", 180.00, "USD", peso_kg=0.6)
    b = simular(cfg, "Motorola Moto G84 5G 256GB", 180.00, "USD", peso_kg=0.6)
    for mod in (Modalidade.ML_CLASSICO, Modalidade.ML_PREMIUM):
        for f in FAIXAS:
            assert (a.modalidades[mod].alvos[f].preco_sugerido_brl
                    == b.modalidades[mod].alvos[f].preco_sugerido_brl)
