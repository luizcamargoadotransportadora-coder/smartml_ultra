"""
SmartML Ultra - Scraper Cirúrgico (Bypass WAF Cloudflare + Exclusão Nativa ML)
"""
import re
import urllib.request
import urllib.parse
import json
from typing import Dict

def buscar_menor_preco_ml(termo_busca: str, custo_compra: float = 0.0) -> Dict:
    termo_base = str(termo_busca).strip()
    
    # 1. BYPASS DO WAF (Cloudflare)
    # APIs do ML bloqueiam 'Mozilla/5.0' vindo de Data Centers (Render). 
    # Usamos uma identidade de aplicação Server-to-Server para passe livre.
    headers = {
        "User-Agent": "SmartMLEngine/2.0",
        "Accept": "application/json"
    }
    
    # ==========================================
    # 2. MODO SNIPER (Links Diretos ou IDs MLB exatos)
    # ==========================================
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
                                "auditoria_ia": "🎯 Anúncio Exato (Sniper Direto)"
                            }
            except Exception:
                pass
        
        match_slug = re.search(r'mercadolivre\.com\.br/([^/]+)', termo_base)
        if match_slug:
            slug = match_slug.group(1).replace("-", " ")
            if "MLB" not in slug: 
                termo_base = slug

    # ==========================================
    # 3. FILTRO NATIVO NO ML E CASCATA (O Fim das Capinhas)
    # ==========================================
    termos_exclusao = ["capa", "case", "pelicula", "película", "cabo", "carregador", "sucata", "defeito", "fone", "bateria"]
    query_limpa = re.sub(r'[-–—_+,;:\(\)\[\]\/\*]', ' ', termo_base)
    
    palavras_busca = query_limpa.lower().split()
    
    # Só adiciona a exclusão (-capa) se a palavra já não estiver na busca original do usuário
    exclusoes = [f"-{exc}" for exc in termos_exclusao if exc not in palavras_busca]
    sufixo_exclusao = " ".join(exclusoes)

    # Prepara a cascata (Remove capacidades se a busca exata falhar para achar a família do produto)
    termo_sem_capacidade = re.sub(r'\b(64|128|256|512)\s*(gb|tb)?\b', '', query_limpa, flags=re.IGNORECASE)
    termo_sem_capacidade = " ".join(termo_sem_capacidade.split())
    termo_curto = " ".join(palavras_busca[:3]) if len(palavras_busca) >= 3 else query_limpa

    tentativas = [
        query_limpa,
        termo_sem_capacidade,
        termo_curto
    ]
    # Limpa duplicadas
    tentativas = list(dict.fromkeys([t for t in tentativas if t.strip()]))

    for tentativa in tentativas:
        # Injeta a exclusão no próprio motor de busca do Mercado Livre
        query_final = f"{tentativa} {sufixo_exclusao}".strip()
        url_api = f"https://api.mercadolibre.com/sites/MLB/search?q={urllib.parse.quote(query_final)}&limit=50"
        
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
                        
                        # Trava financeira absoluta: garante que lixo não indexado passe (abaixo de 30% do custo)
                        if custo_compra > 0 and preco < (custo_compra * 0.30): continue

                        link = item.get('permalink', '').split('?')[0]
                        titulo = item.get('title', '')
                        
                        if not link or "mercadolivre.com.br" not in link:
                            continue

                        candidatos.append({"preco": preco, "link": link, "titulo": titulo})

                    if candidatos:
                        # Ordena estritamente do menor para o maior preço de mercado
                        candidatos.sort(key=lambda x: x["preco"])
                        melhor = candidatos[0]
                        return {
                            "encontrado": True,
                            "menor_preco": melhor["preco"],
                            "link": melhor["link"],
                            "titulo_encontrado": melhor["titulo"],
                            "auditoria_ia": f"⚡ Extração Real Limpa (Query: '{tentativa}')"
                        }
        except Exception as e:
            print(f"Aviso API ML para '{tentativa}': {e}")
            continue

    # Se a API confirmar que o produto literalmente não existe ou não atende a base de custo, retorna de forma clara
    return {
        "encontrado": False,
        "mensagem": "❌ PRODUTO INEXISTENTE OU SEM OFERTAS VÁLIDAS NO ML.<br><br>Utilize o <b>LINK EXATO</b> do anúncio para forçar a leitura."
    }