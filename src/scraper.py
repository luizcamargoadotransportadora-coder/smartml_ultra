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
            return data

    except Exception as e:
        log.error(f"Erro ao consultar no local: {e}")
        return {"encontrado": False, "mensagem": f"Erro conexao tunnel: {str(e)}"}
