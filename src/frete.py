"""src/frete.py — Motor de cálculo de frete (SmartML Ultra v100.0)"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ResultadoFrete:
    peso_real_kg: float
    peso_cubado_kg: float
    peso_faturado_kg: float
    faixa_aplicada: Optional[float]
    custo_tabela_brl: float
    custo_embalagem_brl: float
    custo_total_brl: float
    frete_gratis_ativo: bool
    percentual_vendedor: float
    custo_vendedor_brl: float
    avisos: List[str] = field(default_factory=list)

    def resumo(self) -> str:
        linhas = [
            "=" * 46,
            "  RESUMO DO FRETE",
            "=" * 46,
            f"Peso real .............. {self.peso_real_kg:.3f} kg",
            f"Peso cubado ............ {self.peso_cubado_kg:.3f} kg",
            f"Peso faturado .......... {self.peso_faturado_kg:.3f} kg",
            f"Faixa aplicada ......... {self.faixa_aplicada} kg",
            f"Custo tabela ........... R$ {self.custo_tabela_brl:.2f}",
            f"Custo embalagem ........ R$ {self.custo_embalagem_brl:.2f}",
            f"CUSTO TOTAL ............ R$ {self.custo_total_brl:.2f}",
            f"Frete grátis ........... {'SIM' if self.frete_gratis_ativo else 'NAO'}",
            f"% pago pelo vendedor ... {self.percentual_vendedor * 100:.1f}%",
            f"CUSTO DO VENDEDOR ...... R$ {self.custo_vendedor_brl:.2f}",
        ]
        if self.avisos:
            linhas.append("-" * 46)
            linhas.extend(f"[AVISO] {a}" for a in self.avisos)
        linhas.append("=" * 46)
        return "\n".join(linhas)


class CalculadoraFrete:
    """Calcula o custo de frete a partir do bloco 'frete' do parametros.yaml."""

    def __init__(self, config: Dict[str, Any]):
        bloco = (config or {}).get("frete", {}) or {}

        self.faixas = sorted(
            bloco.get("faixas", []) or [],
            key=lambda f: float(f["ate_kg"]),
        )
        if not self.faixas:
            raise ValueError("Nenhuma faixa de frete encontrada em frete.faixas")

        self.divisor_cubagem = float(bloco.get("divisor_cubagem", 6000))
        self.peso_embalagem_kg = float(bloco.get("peso_embalagem_kg", 0.08))
        self.custo_embalagem_brl = float(bloco.get("custo_embalagem_brl", 1.20))
        self.limiar_frete_gratis_brl = float(bloco.get("limiar_frete_gratis_brl", 79.0))
        self.percentual_vendedor = float(bloco.get("percentual_vendedor", 0.50))
        self.custo_acima_faixa_brl = float(bloco.get("custo_acima_faixa_brl", 0.0))

    # ------------------------------------------------------------------
    def peso_cubado(self, comprimento_cm: float, largura_cm: float, altura_cm: float) -> float:
        volume = float(comprimento_cm) * float(largura_cm) * float(altura_cm)
        return volume / self.divisor_cubagem

    def buscar_faixa(self, peso_kg: float):
        for faixa in self.faixas:
            if peso_kg <= float(faixa["ate_kg"]):
                return float(faixa["ate_kg"]), float(faixa["custo_brl"])
        return None, None

    # ------------------------------------------------------------------
    def calcular(
        self,
        peso_kg: float,
        comprimento_cm: float,
        largura_cm: float,
        altura_cm: float,
        preco_venda_brl: float = 0.0,
    ) -> ResultadoFrete:
        avisos: List[str] = []

        if peso_kg <= 0:
            raise ValueError("peso_kg deve ser maior que zero")
        for nome, valor in (
            ("comprimento_cm", comprimento_cm),
            ("largura_cm", largura_cm),
            ("altura_cm", altura_cm),
        ):
            if valor <= 0:
                raise ValueError(f"{nome} deve ser maior que zero")

        peso_real = float(peso_kg)
        cubado = self.peso_cubado(comprimento_cm, largura_cm, altura_cm)
        faturado = max(peso_real, cubado) + self.peso_embalagem_kg

        if cubado > peso_real:
            avisos.append("Peso cubado venceu o peso real (volume domina).")

        faixa, custo_tabela = self.buscar_faixa(faturado)

        if faixa is None:
            maior = self.faixas[-1]
            faixa = float(maior["ate_kg"])
            custo_tabela = float(maior["custo_brl"]) + self.custo_acima_faixa_brl
            avisos.append(
                f"Peso faturado {faturado:.3f} kg excede a maior faixa "
                f"({faixa} kg). Cotacao manual recomendada."
            )

        custo_total = custo_tabela + self.custo_embalagem_brl

        frete_gratis = float(preco_venda_brl) >= self.limiar_frete_gratis_brl
        percentual = self.percentual_vendedor if frete_gratis else 1.0
        custo_vendedor = round(custo_total * percentual, 2)

        if frete_gratis:
            avisos.append(
                f"Preco >= R$ {self.limiar_frete_gratis_brl:.2f}: "
                f"programa de frete gratis ativo."
            )

        return ResultadoFrete(
            peso_real_kg=round(peso_real, 3),
            peso_cubado_kg=round(cubado, 3),
            peso_faturado_kg=round(faturado, 3),
            faixa_aplicada=faixa,
            custo_tabela_brl=round(custo_tabela, 2),
            custo_embalagem_brl=round(self.custo_embalagem_brl, 2),
            custo_total_brl=round(custo_total, 2),
            frete_gratis_ativo=frete_gratis,
            percentual_vendedor=percentual,
            custo_vendedor_brl=custo_vendedor,
            avisos=avisos,
        )


def _extrair_bloco_frete(config) -> dict:
    """Aceita dict, objeto Pydantic ou None. Se nao achar 'frete', le o YAML."""
    bloco = None

    # 1) dict comum
    if isinstance(config, dict):
        bloco = config.get("frete")

    # 2) objeto Pydantic / qualquer objeto com atributo
    if bloco is None and config is not None:
        bloco = getattr(config, "frete", None)
        if bloco is not None and not isinstance(bloco, dict):
            if hasattr(bloco, "model_dump"):
                bloco = bloco.model_dump()
            elif hasattr(bloco, "dict"):
                bloco = bloco.dict()

    # 3) fallback: ler direto do YAML
    if not bloco:
        import yaml
        from pathlib import Path
        caminho = Path(__file__).resolve().parents[1] / "config" / "parametros.yaml"
        if caminho.exists():
            with open(caminho, "r", encoding="utf-8") as f:
                bruto = yaml.safe_load(f) or {}
            bloco = bruto.get("frete")

    if not bloco:
        raise ValueError(
            "Bloco 'frete' nao encontrado. Verifique config/parametros.yaml."
        )
    return bloco


def criar_calculadora(config=None) -> "CalculadoraFrete":
    return CalculadoraFrete({"frete": _extrair_bloco_frete(config)})
