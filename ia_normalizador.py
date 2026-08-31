import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def auditar_anuncio(termo_original: str, titulo_anuncio: str, preco: float, custo: float) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return json.dumps({"erro": "GEMINI_API_KEY ausente"})

    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Você é um auditor de qualidade de precificação para e-commerce brasileiro.
    Sua função é detectar incoerência semântica e de ordem de grandeza. Você NÃO calcula margens.
    
    DADOS DA ANÁLISE:
    - O que o cliente buscou: "{termo_original}"
    - Título do anúncio encontrado: "{titulo_anuncio}"
    - Preço do anúncio: R$ {preco}
    - Custo de compra da nossa empresa: R$ {custo}
    
    REGRAS DE REPROVAÇÃO (VEREDITO: "bloquear"):
    1. Se o anúncio for de um ACESSÓRIO (capa, cabo, película, caixa vazia).
    2. Se o anúncio indicar PRODUTO NÃO-NOVO (usado, seminovo, recondicionado, vitrine, mostruário, caixa aberta).
    3. Se houver divergência clara de MODELO ou CAPACIDADE (ex: buscou 256GB, achou 128GB).
    4. Incoerência de grandeza (ex: preço muito abaixo do custo, indicando que é apenas uma peça/sucata).
    
    Responda EXATAMENTE neste formato JSON:
    {{
        "veredito": "aprovado" ou "bloquear",
        "motivo": "Frase curta, direta e técnica explicando a decisão."
    }}
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        return response.text
    except Exception as e:
        return json.dumps({"erro": str(e)})

if __name__ == "__main__":
    print("\n--- TESTE DO AUDITOR (IA #2) ---")
    
    # Simulando um falso positivo perigoso: o motor achou uma sucata cara ou um modelo inferior
    termo = "iPhone 15 Pro Max 256 GB"
    anuncio_falso_positivo = "Iphone 15 Pro 128gb Vitrine Impecável - Leia A Descrição"
    preco_achado = 4500.00
    custo_base = 5000.00
    
    print(f"Buscado: '{termo}'")
    print(f"Candidato: '{anuncio_falso_positivo}' (R$ {preco_achado})")
    print("Auditando...\n")
    
    resultado = auditar_anuncio(termo, anuncio_falso_positivo, preco_achado, custo_base)
    
    try:
        parsed = json.loads(resultado)
        print("Veredito Estruturado:")
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    except Exception:
        print(resultado)