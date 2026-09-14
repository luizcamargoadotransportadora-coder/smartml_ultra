import os, logging, urllib.parse
import urllib.request, json

log = logging.getLogger("smartml.scraper")

def buscar_menor_preco_ml(termo, custo_base=0.0):
    try:
        tunnel_url = os.getenv("LOCAL_SCRAPER_URL", "https://ltd-developer-wed-drives.trycloudflare.com").rstrip("/")
        termo_encoded = urllib.parse.quote(termo)
        url_chamada = f"{tunnel_url}/buscar?termo={termo_encoded}&custo={custo_base}"

        req = urllib.request.Request(url_chamada, headers={"User-Agent": "SmartML-Cloud/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if not data.get("sucesso"):
            return {"sucesso": False, "mensagem": data.get("mensagem", "Nenhum concorrente encontrado.")}

        candidatos = data.get("candidatos", [])
        if candidatos:
            melhor = candidatos[0]
            return {
                "sucesso": True,
                "menor_preco": melhor["preco"],
                "link": melhor["link"],
                "titulo_encontrado": melhor["titulo"],
                "imagem": melhor.get("imagem", "")
            }

        if "menor_preco" in data:
            return data

        return {"sucesso": False, "mensagem": "Nenhum anúncio qualificado encontrado."}

    except Exception as e:
        log.error(f"Erro ao consultar radar local: {e}")
        return {"sucesso": False, "mensagem": f"Erro no radar de concorrencia: {str(e)}"}
