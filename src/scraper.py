"""
SmartML Ultra - Módulo de Scraper e Auditoria de Precisão (NLP) + Busca em Cascata
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
    if not texto: return ""
    texto = texto.lower().replace("-", " ")
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

class AuditorIAUltra:
    @staticmethod
    def auditar(termo_busca: str, titulo_anuncio: str) -> Dict:
        termo_norm = normalizar_texto(termo_busca)
        titulo_norm = normalizar_texto(titulo_anuncio)

        for termo_ruim in TERMOS_EXCLUIDOS_CONDICAO:
            if termo_ruim in titulo_norm:
                return {"aprovado": False, "motivo": f"Item Não-Novo"}

        nums_termo = re.findall(r'\b\d+\b', termo_norm)
        for num in nums_termo:
            if len(num) >= 2 or num in ["5", "4", "3"]:
                if num not in titulo_norm:
                    return {"aprovado": False, "motivo": f"Falta '{num}'"}

        for cor_chave, variacoes in MAPA_CORES.items():
            if cor_chave in termo_norm or any(v in termo_norm for v in variacoes):
                todas = [cor_chave] + variacoes
                if not any(v in titulo_norm for v in todas):
                    return {"aprovado": False, "motivo": "Divergência de cor"}

        palavras_ruins_filtradas = [p for p in PALAVRAS_EXCLUIDAS_ACESSORIOS if p not in termo_norm]
        if any(exc in titulo_norm for exc in palavras_ruins_filtradas):
            return {"aprovado": False, "motivo": "Acessório incompatível"}

        return {"aprovado": True, "motivo": "⚡ Auditado por IA"}

def buscar_menor_preco_ml(termo_busca: str, custo_compra: float = 0.0) -> Dict:
    termo_base = str(termo_busca).strip()
    
    # ==========================================
    # 1. MODO SNIPER (FALLBACK PARA LINKS/ID)
    # ==========================================
    match_mlb = re.search(r'MLB[-_]?\s*(\d+)', termo_base, re.IGNORECASE)
    if match_mlb:
        mlb_id = f"MLB{match_mlb.group(1)}"
        url_item = f"https://api.mercadolibre.com/items/{mlb_id}"
        try:
            req = urllib.request.Request(url_item, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    item = json.loads(response.read().decode('utf-8'))
                    preco = float(item.get('price', 0.0))
                    if preco > 0:
                        return {
                            "encontrado": True, "menor_preco": preco,
                            "link": item.get('permalink', '').split('?')[0],
                            "titulo_encontrado": item.get('title', ''),
                            "auditoria_ia": "🎯 Anúncio Exato (Sniper)"
                        }
        except Exception:
            pass # Se o ID falhar, segue para a busca por texto

    # ==========================================
    # 2. BUSCA NORMAL EM CASCATA (TEXTO)
    # ==========================================
    # Limpa pontuações que quebram o ML
    termo_limpo = re.sub(r'[-–—_+,;:\(\)\[\]\/\*]', ' ', termo_base)
    palavras = [p for p in termo_limpo.split() if p]

    # Cria as tentativas de busca (do mais específico ao mais genérico)
    tentativas = [
        termo_base,                    # 1. Exatamente como digitou
        " ".join(palavras[:6]),        # 2. Seis primeiras palavras
        " ".join(palavras[:4])         # 3. Quatro primeiras palavras
    ]

    for tentativa in tentativas:
        if not tentativa.strip(): continue
        
        url_api = f"https://api.mercadolibre.com/sites/MLB/search?q={urllib.parse.quote(tentativa)}&sort=price_asc"
        try:
            req = urllib.request.Request(url_api, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    dados = json.loads(response.read().decode('utf-8'))
                    results = dados.get('results', [])
                    
                    candidatos_validos = []
                    for item in results:
                        if item.get('condition') != 'new': continue
                        preco = float(item.get('price', 0.0))
                        link = item.get('permalink', '').split('?')[0]
                        titulo = item.get('title', '')
                        
                        # Trava contra acessórios muito baratos
                        if custo_compra > 0 and preco < (custo_compra * 0.40): continue

                        # A IA sempre audita contra o termo_base original para garantir a precisão
                        parecer = AuditorIAUltra.auditar(termo_base, titulo)
                        if not parecer["aprovado"]: continue

                        candidatos_validos.append({
                            "preco": preco, "link": link, "titulo": titulo, "auditoria": parecer["motivo"]
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
            continue # Tenta o próximo nível da cascata

    return {"encontrado": False}