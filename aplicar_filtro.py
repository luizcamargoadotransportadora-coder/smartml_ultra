import re

codigo_filtro = '''
def eh_produto_identico(termo_busca: str, titulo_anuncio: str) -> bool:
    import unicodedata
    def normalizar(txt: str) -> str:
        txt = unicodedata.normalize('NFKD', txt).encode('ASCII', 'ignore').decode('utf-8')
        return re.sub(r'[^a-z0-9\s]', ' ', txt.lower())

    t_norm = normalizar(termo_busca)
    a_norm = normalizar(titulo_anuncio)

    # 1. Elimina acessorios se a busca for pelo produto principal
    acessorios = ["capa", "case", "pelicula", "peliculas", "cabo", "carregador", "adaptador", "suporte", "almofada", "borracha", "borrachinha", "cordao"]
    for ac in acessorios:
        if ac not in t_norm and re.search(r'\b' + re.escape(ac) + r'\b', a_norm):
            return False

    # 2. Remove stopwords comuns
    stopwords = {"de", "do", "da", "dos", "das", "para", "com", "em", "e", "ou", "o", "a", "os", "as", "um", "uma"}
    tokens_busca = [t for t in t_norm.split() if t and t not in stopwords]

    if not tokens_busca:
        return True

    # 3. Exige que todas as palavras-chave da busca estejam no titulo do concorrente
    tokens_anuncio = set(a_norm.split())
    for token in tokens_busca:
        if not any(token in tan for tan in tokens_anuncio):
            return False

    return True
'''

with open("local_worker.py", "r", encoding="utf-8") as f:
    conteudo = f.read()

if "def eh_produto_identico" not in conteudo:
    # Insere a funcao de filtro antes do app
    conteudo = codigo_filtro + "\n" + conteudo

# Aplica a condicao no loop de extracao
antigo = 'if p >= piso:'
novo = 'if p >= piso and eh_produto_identico(termo, tit):'

if antigo in conteudo:
    conteudo = conteudo.replace(antigo, novo, 1)
    with open("local_worker.py", "w", encoding="utf-8") as f:
        f.write(conteudo)
    print("[OK] Filtro de produto identico aplicado com sucesso no local_worker.py!")
else:
    print("[AVISO] Trecho de comparacao nao encontrado ou ja atualizado.")
