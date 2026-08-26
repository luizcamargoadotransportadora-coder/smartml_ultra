"""
SmartML Ultra v100.0 - Carregador de configuracoes.
Le config/parametros.yaml, valida e entrega objetos tipados.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml
from pydantic import BaseModel, Field


RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_PADRAO = RAIZ / "config" / "parametros.yaml"


class Projeto(BaseModel):
    nome: str
    versao: str
    ambiente: str


class Custos(BaseModel):
    comissao_marketplace_pct: float = Field(ge=0, le=1)
    imposto_pct: float = Field(ge=0, le=1)
    taxa_financeira_pct: float = Field(ge=0, le=1)
    frete_padrao_brl: float = Field(ge=0)
    embalagem_brl: float = Field(ge=0)
    emite_nf: bool

    @property
    def total_pct(self) -> float:
        return (
            self.comissao_marketplace_pct
            + self.imposto_pct
            + self.taxa_financeira_pct
        )

    @property
    def total_fixo_brl(self) -> float:
        return self.frete_padrao_brl + self.embalagem_brl


class Margem(BaseModel):
    objetivo_pct: float = Field(ge=0, le=1)
    minima_aceitavel_pct: float = Field(ge=0, le=1)
    arredondamento_preco: float


class Classificacao(BaseModel):
    fator_faixa_boa: float = Field(gt=0, le=1)
    registrar_prejuizo: bool
    ordenar_por: str


class Cambio(BaseModel):
    moeda_base: str
    moedas_origem: List[str]
    fonte: str
    cotacoes_manuais: Dict[str, float]
    spread_seguranca_pct: float = Field(ge=0, le=1)


class Scraping(BaseModel):
    base_url: str
    timeout_s: int = Field(gt=0)
    max_retries: int = Field(ge=0)
    backoff_inicial_s: float = Field(ge=0)
    delay_entre_requests_s: float = Field(ge=0)


class Auditoria(BaseModel):
    min_amostras_historico: int = Field(ge=1)
    desvio_max_preco_pct: float = Field(ge=0, le=1)
    score_minimo_oportunidade: float = Field(ge=0, le=1)


class Paths(BaseModel):
    raw: str
    processed: str
    logs: str


class PerfilCategoria(BaseModel):
    descricao: str = ""
    prioridade: int = 50
    comissao_pct: float = Field(ge=0, le=1)
    margem_objetivo_pct: float = Field(ge=0, le=1)
    margem_minima_pct: float = Field(ge=0, le=1)
    lucro_minimo_brl: float = Field(ge=0)
    palavras_chave: List[str] = []


class Configuracao(BaseModel):
    projeto: Projeto
    custos: Custos
    margem: Margem
    classificacao: Classificacao
    cambio: Cambio
    scraping: Scraping
    auditoria: Auditoria
    paths: Paths
    perfis_categoria: Dict[str, PerfilCategoria]

    def perfil(self, nome: str) -> PerfilCategoria:
        """Devolve o perfil pedido ou cai no padrao, sem quebrar."""
        return self.perfis_categoria.get(
            nome, self.perfis_categoria["padrao"]
        )

    def detectar_categoria(self, titulo: str) -> str:
        """Descobre a categoria pelo titulo, respeitando prioridade."""
        texto = titulo.lower()
        candidatos = sorted(
            (
                (perf.prioridade, nome, perf)
                for nome, perf in self.perfis_categoria.items()
                if nome != "padrao"
            ),
            key=lambda item: item[0],
        )
        for _, nome, perf in candidatos:
            for chave in perf.palavras_chave:
                if chave.lower() in texto:
                    return nome
        return "padrao"


def carregar_config(caminho: Path | str | None = None) -> Configuracao:
    """Le o YAML do disco e devolve a configuracao validada."""
    destino = Path(caminho) if caminho else ARQUIVO_PADRAO

    if not destino.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {destino}")

    with open(destino, "r", encoding="utf-8") as f:
        dados = yaml.safe_load(f)

    if not dados:
        raise ValueError(f"Arquivo de configuracao vazio: {destino}")

    cfg = Configuracao(**dados)

    if "padrao" not in cfg.perfis_categoria:
        raise ValueError("O perfil 'padrao' e obrigatorio no YAML.")

    return cfg


if __name__ == "__main__":
    cfg = carregar_config()

    print("=" * 66)
    print(f"  {cfg.projeto.nome} v{cfg.projeto.versao} [{cfg.projeto.ambiente}]")
    print("=" * 66)
    print(f"  Total percentual global : {cfg.custos.total_pct:.1%}")
    print(f"  Total fixo              : R$ {cfg.custos.total_fixo_brl:.2f}")
    print(f"  Perfis carregados       : {len(cfg.perfis_categoria)}")
    print("=" * 66)

    print(
        f"\n  {'PERFIL':<24}{'PRIOR':>6}{'COMIS':>8}"
        f"{'ALVO':>7}{'MIN':>7}{'LUCRO MIN':>12}"
    )
    print("  " + "-" * 62)

    ordenados = sorted(
        cfg.perfis_categoria.items(), key=lambda item: item[1].prioridade
    )
    for nome, p in ordenados:
        print(
            f"  {nome:<24}"
            f"{p.prioridade:>6}"
            f"{p.comissao_pct:>7.1%}"
            f"{p.margem_objetivo_pct:>7.1%}"
            f"{p.margem_minima_pct:>7.1%}"
            f"{p.lucro_minimo_brl:>11.2f}"
        )

    print("\n" + "=" * 66)
    print("  TESTE DE DETECCAO AUTOMATICA")
    print("=" * 66)

    exemplos = [
        "iPhone 16 Pro Max 256GB Lacrado",
        "Motorola Moto G84 5G 256GB",
        "Fone AirPods Pro 2 Original",
        "Notebook Dell Inspiron 15 SSD 512GB",
        "Capa Silicone iPhone 15",
        "Cabo USB C para iPhone 15 Original",
        "Pelicula de vidro Galaxy S24",
        "Panela de pressao 5 litros",
    ]

    for titulo in exemplos:
        cat = cfg.detectar_categoria(titulo)
        marca = "->" if cat != "padrao" else "  "
        print(f"  {marca} {titulo[:40]:<42} {cat}")

    print("=" * 66)
    print("  OK - configuracao e perfis carregados.")
