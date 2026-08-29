"""
SmartML Ultra - Módulo de Scraper Real (Sem Fallbacks Fictícios - Apenas Dados Reais)
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
                                "auditoria_ia": "🎯 Anúncio Exato (Sniper Real)"
                            }
            except Exception:
                pass
        
        # Se for link de catálogo do ML, extrai o termo limpo
        match_slug = re.search(r'mercadolivre\.com\.br/([^/]+)', termo_base)
        if match_slug:
            slug = match_slug.group(1).replace("-", " ")
            if "MLB" not in slug: 
                termo_base = slug

    # 2. BUSCA OFICIAL NA API DO MERCADO LIVRE (DADOS REAIS DE RUA)
    termo_limpo = re.sub(r'[-–—_+,;:\(\)\[\]\/\*]', ' ', termo_base)
    url_api = f"https://api.mercadolibre.com/sites/MLB/search?q={urllib.parse.quote(termo_limpo)}&limit=25"
    
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
                    # Ordena estritamente pelo menor preço real de mercado
                    candidatos.sort(key=lambda x: x["preco"])
                    melhor = candidatos[0]
                    return {
                        "encontrado": True,
                        "menor_preco": melhor["preco"],
                        "link": melhor["link"],
                        "titulo_encontrado": melhor["titulo"],
                        "auditoria_ia": "⚡ Extração Real de Mercado"
                    }
    except Exception as e:
        print(f"Erro na API ML: {e}")

    # 3. FALHA CONTROLADA: Sem dados inventados. Se o mercado não retornar, o sistema avisa o operador.
    return {
        "encontrado": False,
        "mensagem": "❌ CONCORRENTE NÃO ENCONTRADO.<br><br>Insira o <b>LINK DIRETO</b> do anúncio do Mercado Livre para capturar o link real e o menor preço exato."
    }