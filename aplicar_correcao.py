with open("src/main.py", "r", encoding="utf-8") as f:
    main_py = f.read()

if '"custo_base":' not in main_py:
    main_py = main_py.replace(
        '"titulo": titulo_encontrado,',
        '"titulo": titulo_encontrado,\n            "titulo_encontrado": titulo_encontrado,\n            "custo_base": entrada.custo,'
    )
    with open("src/main.py", "w", encoding="utf-8") as f:
        f.write(main_py)
    print("[OK] src/main.py atualizado com sucesso!")
else:
    print("[INFO] src/main.py ja contem custo_base.")

with open("static/index.html", "r", encoding="utf-8") as f:
    html = f.read()

if "res.custo_base.toFixed" in html:
    html = html.replace("res.custo_base.toFixed(2)", "(res.custo_base || custo || 0).toFixed(2)")
    with open("static/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("[OK] static/index.html atualizado com sucesso!")
else:
    print("[INFO] static/index.html ja protegido.")
