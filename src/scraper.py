"""
SmartML Ultra - Scraper com Relaxamento Automático de Termos e Resiliência Total
"""
import re
import urllib.request
import urllib.parse
import json
from typing import Dict

def buscar_menor_preco_ml(termo_busca: str, custo_compra: float = 0.0) -> Dict:
    termo_base = str(termo_busca).strip()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    # 1. MODO SNIPER (Links Diretos ou IDs MLB exatos)
    match_item = re.search(r'MLB[-_]?(\d+)', termo_base, re.IGNORECASE)
    if "mercadolivre.com.br" in termo_base or match_item:
        if match_item:
            mlb_id = f"MLB{match_item.group(1)}"
            url_item = f"https://api.mercadolibre.com/items/{mlb_id}"
            try:
                req = urllib.request.Request(url_item, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        item = json.loads(response.read().decode('utf-8'))
                        preco = float(item.get('price', 0.0))
                        link_real = item.get('permalink', '').split('?')[0]
                        titulo_real = item.get('title', '')
                        if preco > 0 and link_real:
                            return {
                                "encontrado": True, 
                                "menor_preco": preco,
                                "link": link_real,
                                "titulo_encontrado": titulo_real,
                                "auditoria_ia": "🎯 Anúncio Exato (Modo Sniper)"
                            }
            except Exception:
                pass
        
        match_slug = re.search(r'mercadolivre\.com\.br/([^/]+)', termo_base)
        if match_slug:
            slug = match_slug.group(1).replace("-", " ")
            if "MLB" not in slug: 
                termo_base = slug

    # 2. CONSTRUÇÃO DE TENTATIVAS COM RELAXAMENTO DE TERMOS (CASCATA INTELIGENTE)
    # Remove capacidades (ex: 256gb, 128gb) e termos genéricos para encontrar o produto base no ML se necessário
    termo_limpo = re.sub(r'[-–—_+,;:\(\)\[\]\/\*]', ' ', termo_base)
    
    # Tentativa 1: Termo original limpo
    # Tentativa 2: Remove especificações de armazenamento (ex: 128gb, 256gb, 512gb, 1tb) para achar o modelo
    termo_sem_capacidade = re.sub(r'\b(64|128|256|512)\s*(gb|tb)?\b', '', termo_limpo, flags=re.IGNORECASE)
    termo_sem_capacidade = " ".join(termo_sem_capacidade.split())

    palavras = [p for p in termo_limpo.split() if p]
    termo_curto = " ".join(palavras[:3]) if len(palavras) >= 3 else termo_limpo

    tentativas = [
        termo_base,
        termo_limpo,
        termo_sem_capacidade,
        termo_curto
    ]
    # Remove duplicadas mantendo a ordem
    tentativas = list(dict.fromkeys([t for t in tentativas if t.strip()]))

    for tentativa in tentativas:
        url_api = f"https://api.mercadolibre.com/sites/MLB/search?q={urllib.parse.quote(tentativa)}&limit=40"
        
        try:
            req = urllib.request.Request(url_api, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    dados = json.loads(response.read().decode('utf-8'))
                    results = dados.get('results', [])
                    
                    candidatos = []
                    for item in results:
                        preco = float(item.get('price', 0.0))
                        if preco <= 0: continue
                        
                        # Trava financeira de segurança (desacopla acessórios absurdamente baratos)
                        if custo_compra > 0 and preco < (custo_compra * 0.20): continue

                        link = item.get('permalink', '').split('?')[0]
                        titulo = item.get('title', '')
                        
                        titulo_lower = titulo.lower()
                        if any(x in titulo_lower for x in ["com defeito", "para peças", "quebrado", "carcaça"]):
                            continue

                        if not link or "mercadolivre.com.br" not in link:
                            continue

                        candidatos.append({"preco": preco, "link": link, "titulo": titulo})

                    if candidatos:
                        # Ordena estritamente pelo menor preço real de mercado
                        candidatos.sort(key=lambda x: x["preco"])
                        melhor = candidatos[0]
                        return {
                            "encontrado": True,
                            "menor_preco": melhor["preco"],
                            "link": melhor["link"],
                            "titulo_encontrado": melhor["titulo"],
                            "auditoria_ia": f"⚡ Extração Real (Busca: '{tentativa}')"
                        }
        except Exception as e:
            print(f"Erro na tentativa '{tentativa}': {e}")
            continue

    return {
        "encontrado": False,
        "mensagem": "❌ PRODUTO NÃO ENCONTRADO.<br><br>Cole o <b>LINK EXATO</b> do Mercado Livre."
    }