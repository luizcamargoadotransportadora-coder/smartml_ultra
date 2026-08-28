"""
SmartML Ultra - Módulo de Scraper e Auditoria de Precisão (NLP)
Filtra anúncios garantindo apenas produtos novos, com cores, modelos exatos e sem acessórios indesejados.
"""

import re
import unicodedata
import urllib.request
import urllib.parse
import json
from typing import Dict, Optional

TERMOS_EXCLUIDOS_CONDICAO = [
    "usado", "usados", "seminovo", "semi novo", "recondicionado", 
    "caixa aberta", "caixa-aberta", "open box", "openbox", "mostruario", 
    "mostruário", "vitrine", "com defeito", "para peças", "tela trincada", 
    "reballed", "refurbished", "outlet"
]

PALAVRAS_EXCLUIDAS_ACESSORIOS = [
    "capa", "capinha", "película", "pelicula", "cabo", "case", "suporte",
    "carregador", "proteção", "protecao", "vidro", "defeito", "peças"
]

MAPA_CORES = {
    "laranja": ["laranja", "cosmico", "cosmica", "orange", "copper"],
    "titanio": ["titanio", "titanium", "natural", "deserto"],
    "preto": ["preto", "black", "grafite", "dark", "negro"],
    "branco": ["branco", "white", "silver", "prata"],
    "azul": ["azul", "blue", "navy"],
    "verde": ["verde", "green"]
}


def normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.lower().replace("-", " ")
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


class AuditorIAUltra:
    @staticmethod
    def auditar(termo_busca: str, titulo_anuncio: str) -> Dict:
        termo_norm = normalizar_texto(termo_busca)
        titulo_norm = normalizar_texto(titulo_anuncio)

        # 1. Filtro Estrito: Condições indesejadas (Usado, Caixa Aberta, Vitrine, etc.)
        for termo_ruim in TERMOS_EXCLUIDOS_CONDICAO:
            if termo_ruim in titulo_norm:
                return {
                    "aprovado": False,
                    "motivo": f"Descartado: Item Não-Novo ('{termo_ruim.upper()}')"
                }

        # 2. Validação dos Números do Modelo (Ex: 17, 256, etc.)
        nums_termo = re.findall(r'\b\d+\b', termo_norm)
        for num in nums_termo:
            if len(num) >= 2 or num in ["5", "4", "3"]:
                if num not in titulo_norm:
                    return {
                        "aprovado": False,
                        "motivo": f"Divergência: número '{num}' ausente no anúncio"
                    }

        # 3. Validação de Cor
        for cor_chave, variacoes in MAPA_CORES.items():
            if cor_chave in termo_norm or any(v in termo_norm for v in variacoes):
                todas = [cor_chave] + variacoes
                if not any(v in titulo_norm for v in todas):
                    return {
                        "aprovado": False,
                        "motivo": f"Divergência de cor: Solicitado '{cor_chave.upper()}'"
                    }

        # 4. Trava de Acessórios (Se a busca principal não for por capa, bloqueia capas)
        palavras_ruins_filtradas = [
            p for p in PALAVRAS_EXCLUIDAS_ACESSORIOS if p not in termo_norm
        ]
        if any(exc in titulo_norm for exc in palavras_ruins_filtradas):
            return {
                "aprovado": False,
                "motivo": "Anúncio é um acessório incompatível"
            }

        return {
            "aprovado": True,
            "motivo": "⚡ Auditado por IA de precisão avançada"
        }


def buscar_menor_preco_ml(termo_busca: str, custo_compra: float = 0.0) -> Optional[Dict]:
    """
    Varre a API pública do Mercado Livre aplicando a auditoria estrita de novos e modelos.
    """
    termo_base = str(termo_busca).strip()
    url_api = f"https://api.mercadolibre.com/sites/MLB/search?q={urllib.parse.quote(termo_base)}&sort=price_asc"
    
    try:
        req = urllib.request.Request(
            url_api, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                dados = json.loads(response.read().decode('utf-8'))
                results = dados.get('results', [])
                
                candidatos_validos = []
                for item in results:
                    # Exige estritamente que o produto seja novo
                    if item.get('condition') != 'new':
                        continue
                    
                    titulo = item.get('title', '')
                    preco = float(item.get('price', 0.0))
                    link = item.get('permalink', '').split('?')[0]
                    
                    # Trava contábil: descarta absurdos operacionais (preço menor que 40% do custo)
                    if custo_compra > 0 and preco < (custo_compra * 0.40):
                        continue

                    # Executa a auditoria de IA nos títulos
                    parecer = AuditorIAUltra.auditar(termo_base, titulo)
                    if not parecer["aprovado"]:
                        continue

                    candidatos_validos.append({
                        "preco": preco,
                        "link": link,
                        "titulo": titulo,
                        "auditoria": parecer["motivo"]
                    })

                if candidatos_validos:
                    candidatos_validos.sort(key=lambda x: x["preco"])
                    melhor = candidatos_validos[0]
                    return {
                        "encontrado": True,
                        "menor_preco": melhor["preco"],
                        "link": melhor["link"],
                        "titulo_encontrado": melhor["titulo"],
                        "auditoria_ia": melhor["auditoria"]
                    }
    except Exception as e:
        print(f"Erro na busca API ML: {e}")

    return {"encontrado": False}