"""
SmartML Ultra - Módulo de Scraper Oficial Autenticado (Client Credentials + Anti-Bloqueio Nuvem)
"""
import re
import urllib.request
import urllib.parse
import json
from typing import Dict, Optional

# Credenciais Oficiais da Aplicação SmartMLEngine
CLIENT_ID = "6903491647062278"
CLIENT_SECRET = "qm1v0B0xZNhoMB0qtSH6T6wk814L5n4e"

_TOKEN_CACHE = None

def _obter_token_oficial() -> Optional[str]:
    """Gera o token OAuth de forma automatizada para liberar o acesso via Render."""
    global _TOKEN_CACHE
    if _TOKEN_CACHE:
        return _TOKEN_CACHE

    url = "https://api.mercadolibre.com/oauth/token"
    payload = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "SmartMLEngine/1.0"
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                _TOKEN_CACHE = data.get("access_token")
                return _TOKEN_CACHE
    except Exception as e:
        print(f"Erro OAuth ML: {e}")
    return None

def buscar_menor_preco_ml(termo_busca: str, custo_compra: float = 0.0) -> Dict:
    termo_base = str(termo_busca).strip()
    token = _obter_token_oficial()
    
    headers = {
        "User-Agent": "SmartMLEngine/1.0",
        "Accept": "application/json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

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
                                "auditoria_ia": "🎯 Anúncio Exato (Sniper Oficial)"
                            }
            except Exception:
                pass
        
        match_slug = re.search(r'mercadolivre\.com\.br/([^/]+)', termo_base)
        if match_slug:
            slug = match_slug.group(1).replace("-", " ")
            if "MLB" not in slug: 
                termo_base = slug

    # 2. BUSCA OFICIAL AUTENTICADA NA API DO MERCADO LIVRE
    termo_limpo = re.sub(r'[-–—_+,;:\(\)\[\]\/\*]', ' ', termo_base)
    url_api = f"https://api.mercadolibre.com/sites/MLB/search?q={urllib.parse.quote(termo_limpo)}&limit=30"
    
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
                    if custo_compra > 0 and preco < (custo_compra * 0.25): continue

                    link = item.get('permalink', '').split('?')[0]
                    titulo = item.get('title', '')
                    
                    titulo_lower = titulo.lower()
                    if any(x in titulo_lower for x in ["pelicula", "capa", "case", "cabo", "carregador", "película"]):
                        continue

                    if not link or "mercadolivre.com.br" not in link:
                        continue

                    candidatos.append({"preco": preco, "link": link, "titulo": titulo})

                if candidatos:
                    candidatos.sort(key=lambda x: x["preco"])
                    melhor = candidatos[0]
                    return {
                        "encontrado": True,
                        "menor_preco": melhor["preco"],
                        "link": melhor["link"],
                        "titulo_encontrado": melhor["titulo"],
                        "auditoria_ia": "⚡ Extração Oficial Autorizada"
                    }
    except Exception as e:
        print(f"Erro na API Oficial do ML: {e}")

    return {
        "encontrado": False,
        "mensagem": "❌ PRODUTO NÃO ENCONTRADO PELA API.<br><br>Cole o <b>LINK EXATO</b> do Mercado Livre no campo de busca para captura direta."
    }