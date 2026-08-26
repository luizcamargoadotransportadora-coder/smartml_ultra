"""
SmartML Ultra v100.0 - Testes do modulo de modalidades.
Blinda as faixas oficiais do Mercado Livre antes da integracao.
"""
from __future__ import annotations

import pytest

from src.modalidades import (
    COMISSAO_PADRAO,
    LIMITE_CLASSICO,
    LIMITE_PREMIUM,
    TABELA_COMISSAO,
    TICKET_MINIMO_PREMIUM_BRL,
    Modalidade,
    comissao_de,
    comparar_modalidades,
    dentro_da_faixa_oficial,
    diferenca_premium_classico,
    perfil_modalidade,
)


# ----------------------------------------------------------------- enum
def test_enum_tem_as_duas_modalidades():
    assert Modalidade.ML_CLASSICO.value == "ML_CLASSICO"
    assert Modalidade.ML_PREMIUM.value == "ML_PREMIUM"


def test_rotulo_legivel():
    assert Modalidade.ML_CLASSICO.rotulo == "Classico"
    assert Modalidade.ML_PREMIUM.rotulo == "Premium"


def test_apenas_premium_tem_parcelamento():
    assert Modalidade.ML_PREMIUM.parcela_sem_juros == 12
    assert Modalidade.ML_CLASSICO.parcela_sem_juros == 0


# ------------------------------------------------- faixas oficiais do ML
@pytest.mark.parametrize("categoria", list(TABELA_COMISSAO))
def test_classico_dentro_da_faixa_oficial(categoria):
    pct = comissao_de(categoria, Modalidade.ML_CLASSICO)
    baixo, alto = LIMITE_CLASSICO
    assert baixo <= pct <= alto


@pytest.mark.parametrize("categoria", list(TABELA_COMISSAO))
def test_premium_dentro_da_faixa_oficial(categoria):
    pct = comissao_de(categoria, Modalidade.ML_PREMIUM)
    baixo, alto = LIMITE_PREMIUM
    assert baixo <= pct <= alto


@pytest.mark.parametrize("categoria", list(TABELA_COMISSAO))
def test_premium_sempre_custa_mais_que_classico(categoria):
    classico = comissao_de(categoria, Modalidade.ML_CLASSICO)
    premium = comissao_de(categoria, Modalidade.ML_PREMIUM)
    assert premium > classico


def test_faixas_nao_se_sobrepoem():
    """O teto do Classico nao pode alcancar o piso do Premium."""
    assert LIMITE_CLASSICO[1] < LIMITE_PREMIUM[0]


# ------------------------------------------------------ valor de negocio
def test_celular_premium_confere_com_o_parametro_do_usuario():
    """16,5% e o valor Premium de referencia do projeto."""
    assert comissao_de("celular", Modalidade.ML_PREMIUM) == pytest.approx(0.165)


def test_categoria_aceita_maiuscula_e_espaco():
    assert comissao_de("  CELULAR  ", Modalidade.ML_PREMIUM) == pytest.approx(
        comissao_de("celular", Modalidade.ML_PREMIUM)
    )


def test_categoria_desconhecida_cai_no_padrao():
    pct = comissao_de("categoria_que_nao_existe", Modalidade.ML_PREMIUM)
    assert pct == pytest.approx(COMISSAO_PADRAO[Modalidade.ML_PREMIUM])


def test_categoria_none_cai_em_geral():
    assert comissao_de(None, Modalidade.ML_CLASSICO) == pytest.approx(
        comissao_de("geral", Modalidade.ML_CLASSICO)
    )


def test_modalidade_como_texto_e_aceita():
    perfil = perfil_modalidade("celular", "ML_PREMIUM")
    assert perfil.modalidade is Modalidade.ML_PREMIUM


# ------------------------------------------------------------- diferenca
def test_diferenca_premium_classico_e_positiva():
    assert diferenca_premium_classico("celular") > 0


def test_diferenca_celular_e_cinco_pontos():
    assert diferenca_premium_classico("celular") == pytest.approx(0.05)


def test_comparar_devolve_as_tres_chaves():
    c = comparar_modalidades("informatica")
    assert set(c) == {"classico_pct", "premium_pct", "diferenca_pp"}
    assert c["premium_pct"] > c["classico_pct"]


# ---------------------------------------------------------------- avisos
def test_ticket_baixo_avisa_para_usar_classico():
    perfil = perfil_modalidade(
        "acessorio", Modalidade.ML_PREMIUM, preco_referencia_brl=18.00
    )
    assert any("Classico" in a for a in perfil.avisos)


def test_ticket_alto_nao_avisa():
    perfil = perfil_modalidade(
        "celular", Modalidade.ML_PREMIUM, preco_referencia_brl=8000.00
    )
    assert not any("Classico" in a for a in perfil.avisos)


def test_classico_nunca_recebe_aviso_de_ticket():
    perfil = perfil_modalidade(
        "acessorio", Modalidade.ML_CLASSICO, preco_referencia_brl=18.00
    )
    assert not any("Classico costuma" in a for a in perfil.avisos)


def test_categoria_desconhecida_gera_aviso():
    perfil = perfil_modalidade("xpto", Modalidade.ML_PREMIUM)
    assert any("fora da tabela" in a for a in perfil.avisos)


def test_categoria_conhecida_sem_avisos():
    perfil = perfil_modalidade("celular", Modalidade.ML_PREMIUM)
    assert perfil.avisos == []


def test_limite_de_ticket_e_o_esperado():
    assert TICKET_MINIMO_PREMIUM_BRL == pytest.approx(200.00)


def test_no_limite_exato_nao_avisa():
    """R$ 200,00 nao dispara: a regra e estritamente menor."""
    perfil = perfil_modalidade(
        "celular", Modalidade.ML_PREMIUM, preco_referencia_brl=200.00
    )
    assert not any("Classico" in a for a in perfil.avisos)


# ------------------------------------------------------------- validacao
def test_valida_faixa_corretamente():
    assert dentro_da_faixa_oficial(0.165, Modalidade.ML_PREMIUM) is True
    assert dentro_da_faixa_oficial(0.25, Modalidade.ML_PREMIUM) is False
    assert dentro_da_faixa_oficial(0.115, Modalidade.ML_CLASSICO) is True
    assert dentro_da_faixa_oficial(0.05, Modalidade.ML_CLASSICO) is False


def test_modalidade_invalida_levanta_erro():
    with pytest.raises(ValueError):
        perfil_modalidade("celular", "ML_TURBO")


def test_perfil_preserva_categoria_normalizada():
    perfil = perfil_modalidade("  Celular ", Modalidade.ML_CLASSICO)
    assert perfil.categoria == "celular"
    assert perfil.rotulo == "Classico"