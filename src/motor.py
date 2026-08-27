"""
motor.py - Orquestrador central do SmartML Ultra v100.0

Recebe os dados de um produto e devolve um resultado consolidado,
juntando precificacao reversa, modalidades, frete e classificacao.

Este e o modulo que a interface (AppSheet/CLI) vai consumir.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from src.precificador import simular, SimulacaoCompleta
from src.classificador import analisar, Resultado

# ---------------------------------------------------------------
# Ordem oficial das faixas (da menos para a mais lucrativa)
# ---------------------------------------------------------------
ORDEM_FAIXAS = ("EMPATE", "MINIMA", "BOA", "OBJETIVO")

# ---------------------------------------------------------------
# Estruturas de saida
# ---------------------------------------------------------------
@dataclass
class OpcaoPreco:
    """Uma combinacao concreta: modalidade + faixa de margem."""
    modalidade: str
    comissao_pct: float
    faixa: str
    preco_sugerido_brl: float
    lucro_brl: float
    margem_pct: float
    frete_brl: float
    classificacao: str
    atende_lucro_minimo: bool

@dataclass
class AnaliseProduto:
    """Resultado consolidado de um produto."""
    titulo: str
    categoria: Optional[str]
    moeda_origem: str
    custo_origem: float
    custo_brl: float
    opcoes: List[OpcaoPreco] = field(default_factory=list)
    recomendada: Optional[OpcaoPreco] = None
    motivo_recomendacao: str = ""
    avisos: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario puro - pronto para JSON/AppSheet."""
        return asdict(self)

# ---------------------------------------------------------------
# Funcoes auxiliares
# ---------------------------------------------------------------
def _frete_do_alvo(alvo) -> float:
    """Extrai o custo de frete de um alvo, de forma tolerante."""
    rf = getattr(alvo, "resultado_frete", None)
    if rf is None:
        return 0.0
    for nome in ("custo_vendedor_brl", "custo_total_brl", "custo_brl", "valor_brl"):
        valor = getattr(rf, nome, None)
        if valor is not None:
            return float(valor)
    return 0.0

def _coletar_avisos(sim: SimulacaoCompleta) -> List[str]:
    """Junta avisos vindos do calculo de frete, sem repetir."""
    avisos: List[str] = []
    for mod_simulacao in sim.modalidades.values():
        for alvo in mod_simulacao.alvos.values():
            rf = getattr(alvo, "resultado_frete", None)
            for aviso in getattr(rf, "avisos", []) or []:
                if aviso not in avisos:
                    avisos.append(aviso)
    return avisos

def _e_critica(opcao: OpcaoPreco) -> bool:
    classificacao = str(opcao.classificacao).upper()
    return "CRITICA" in classificacao or "PREJUIZO" in classificacao

def _escolher(cands: List[OpcaoPreco], estrategia: str) -> Optional[OpcaoPreco]:
    """Aplica a estrategia de recomendacao sobre os candidatos."""
    if not cands:
        return None
    if estrategia == "lucro":
        return max(cands, key=lambda o: o.lucro_brl)
    if estrategia == "equilibrado":
        saudaveis = [o for o in cands if not _e_critica(o)]
        return max(saudaveis or cands, key=lambda o: o.lucro_brl)
    
    return min(cands, key=lambda o: o.preco_sugerido_brl)

# ---------------------------------------------------------------
# Processamento Principal
# ---------------------------------------------------------------
def processar(
    cfg,
    titulo: str,
    custo: float,
    moeda: str = "BRL",
    categoria: Optional[str] = None,
    peso_kg: float = 0.5,
    comprimento_cm: float = 20.0,
    largura_cm: float = 15.0,
    altura_cm: float = 10.0,
    estrategia: str = "equilibrado",
) -> AnaliseProduto:
    """
    Processa um produto de ponta a ponta.
    1) Simula precos em todas as modalidades e faixas.
    2) Classifica cada preco encontrado.
    3) Escolhe a opcao recomendada.
    """
    sim = simular(
        cfg,
        titulo=titulo,
        custo=custo,
        moeda=moeda,
        categoria=categoria,
        peso_kg=peso_kg,
        comprimento_cm=comprimento_cm,
        largura_cm=largura_cm,
        altura_cm=altura_cm,
    )

    opcoes: List[OpcaoPreco] = []

    for mod_simulacao in sim.modalidades.values():
        rotulo_mod = getattr(mod_simulacao.modalidade, "rotulo", str(mod_simulacao.modalidade))

        for alvo in mod_simulacao.alvos.values():
            res: Resultado = analisar(
                cfg,
                titulo=titulo,
                custo_produto_brl=sim.custo_brl,
                preco_venda_brl=alvo.preco_sugerido_brl,
                categoria=categoria,
            )

            opcoes.append(
                OpcaoPreco(
                    modalidade=rotulo_mod,
                    comissao_pct=mod_simulacao.comissao_pct,
                    faixa=alvo.rotulo,
                    preco_sugerido_brl=alvo.preco_sugerido_brl,
                    lucro_brl=alvo.lucro_brl,
                    margem_pct=alvo.margem_pct,
                    frete_brl=_frete_do_alvo(alvo),
                    classificacao=getattr(res.faixa, "value", str(res.faixa)),
                    atende_lucro_minimo=res.atende_lucro_minimo,
                )
            )

    validas = [o for o in opcoes if o.atende_lucro_minimo]
    recomendada = _escolher(validas or opcoes, estrategia) if opcoes else None

    avisos = _coletar_avisos(sim)
    if not validas and opcoes:
        avisos.append("Nenhuma opcao atinge o lucro minimo configurado.")

    return AnaliseProduto(
        titulo=sim.titulo,
        categoria=sim.categoria,
        moeda_origem=sim.moeda_origem,
        custo_origem=sim.custo_origem,
        custo_brl=sim.custo_brl,
        opcoes=opcoes,
        recomendada=recomendada,
        avisos=avisos,
    )

def processar_lote(cfg, produtos: List[Dict[str, Any]]) -> List[AnaliseProduto]:
    """Processa varios produtos de uma vez. Util para planilhas."""
    return [processar(cfg, **produto) for produto in produtos]