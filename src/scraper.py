"""
SmartML Ultra - Módulo de Scraper e Auditoria de Precisão (NLP) + Extrator de URLs + Resgate Inteligente
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
    "carregador", "proteção", "protecao", "vidro", "defeito", "peças", "caixa vazia"
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

        # Regra de Borda (\b) - Evita que 'usado' bloqueie a palavra 'recusado', por exemplo.
        for termo_ruim in TERMOS_EXCLUIDOS_CONDICAO:
            if re.search(r'\b' + re.escape(termo_ruim) + r'\b', titulo_norm):
                return {"aprovado": False, "motivo": f"Item Não-Novo ({termo_ruim})"}

        for cor_chave, variacoes in MAPA_CORES.items():
            if cor_chave in termo_norm or any(v in termo_norm for v in variacoes):
                todas = [cor_chave] + variacoes
                if not any(v in titulo_norm for v in todas):
                    return {"aprovado": False, "motivo": "Divergência de cor"}

        # Regra de Borda (\b) - Evita que 'capa' bloqueie 'capacidade'
        palavras_ruins_filtradas = [p for p in PALAVRAS_EXCLUIDAS_ACESSORIOS if not re.search(r'\b' + re.escape(p) + r'\b', termo_norm)]
        for exc in palavras_ruins_filtradas:
            if re.search(r'\b' + re.escape(exc) + r'\b', titulo_norm):
                return {"aprovado": False, "motivo": f"Acessório incompatível ({exc})"}

        return {"aprovado": True, "motivo": "⚡ Auditado por IA"}

def buscar_menor_preco_ml(termo_busca: str, custo_compra: float = 0.0) -> Dict:
    termo_base = str(termo_busca).strip()
    # Anti-bloqueio de API (simula um navegador real)
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    # ==========================================
    # 1. TRATAMENTO DE LINKS E MODO SNIPER
    # ==========================================
    if "mercadolivre.com.br" in termo_base:
        match_item = re.search(r'MLB[-_]?(\d+)', termo_base, re.IGNORECASE)
        if match_item:
            mlb_id = f"MLB{match_item.group(1)}"
            url_item = f"https://api.mercadolibre.com/items/{mlb_id}"
            try:
                req = urllib.request.Request(url_item, headers=HEADERS)
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
                pass
        
        match_slug = re.search(r'mercadolivre\.com\.br/([^/]+)', termo_base)
        if match_slug:
            slug = match_slug.group(1).replace("-", " ")
            if "MLB" not in slug: 
                termo_base = slug 

    elif re.match(r'^MLB\d+$', termo_base, re.IGNORECASE):
        mlb_id = termo_base.upper()
        url_item = f"https://api.mercadolibre.com/items/{mlb_id}"
        try:
            req = urllib.request.Request(url_item, headers=HEADERS)
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
            return {"encontrado": False}

    # ==========================================
    # 2. BUSCA NORMAL EM CASCATA COM RESGATE
    # ==========================================
    termo_limpo = re.sub(r'[-–—_+,;:\(\)\[\]\/\*]', ' ', termo_base)
    palavras = [p for p in termo_limpo.split() if p]

    tentativas = [
        termo_base,                    
        " ".join(palavras[:6]),        
        " ".join(palavras[:4])         
    ]

    for tentativa in tentativas:
        if not tentativa.strip(): continue
        
        url_api = f"https://api.mercadolibre.com/sites/MLB/search?q={urllib.parse.quote(tentativa)}"
        
        try:
            req = urllib.request.Request(url_api, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    dados = json.loads(response.read().decode('utf-8'))
                    results = dados.get('results', [])
                    
                    candidatos_rigorosos = []
                    candidatos_resgate = []

                    for item in results:
                        if item.get('condition') != 'new': continue
                        preco = float(item.get('price', 0.0))
                        
                        # Trava Matemática Infalível: Bloqueia capinhas e lixo eletrônico
                        if custo_compra > 0 and preco < (custo_compra * 0.40): continue

                        link = item.get('permalink', '').split('?')[0]
                        titulo = item.get('title', '')
                        
                        parecer = AuditorIAUltra.auditar(termo_base, titulo)
                        if parecer["aprovado"]:
                            candidatos_rigorosos.append({
                                "preco": preco, "link": link, "titulo": titulo, "auditoria": parecer["motivo"]
                            })
                        else:
                            candidatos_resgate.append({
                                "preco": preco, "link": link, "titulo": titulo, "auditoria": f"⚠️ Resgate (NLP Falhou)"
                            })

                    # Opção 1: Prioriza as aprovações estritas da IA (Menor preço real)
                    if candidatos_rigorosos:
                        candidatos_rigorosos.sort(key=lambda x: x["preco"])
                        melhor = candidatos_rigorosos[0]
                        return {
                            "encontrado": True,
                            "menor_preco": melhor["preco"],
                            "link": melhor["link"],
                            "titulo_encontrado": melhor["titulo"],
                            "auditoria_ia": melhor["auditoria"]
                        }
                    
                    # Opção 2: Rede de Resgate. Pega o item mais relevante do ML que passou pelo filtro de PREÇO.
                    if candidatos_resgate:
                        melhor = candidatos_resgate[0]
                        return {
                            "encontrado": True,
                            "menor_preco": melhor["preco"],
                            "link": melhor["link"],
                            "titulo_encontrado": melhor["titulo"],
                            "auditoria_ia": melhor["auditoria"]
                        }
        except Exception as e:
            print(f"Erro na API ML: {e}")
            continue 

    return {"encontrado": False}