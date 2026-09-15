with open("local_worker.py", "r", encoding="utf-8") as f:
    codigo = f.read()

antigo = "html = await page_worker.content()"
novo = """html = ""
            for _ in range(5):
                try:
                    await page_worker.wait_for_load_state("domcontentloaded", timeout=4000)
                    html = await page_worker.content()
                    if html:
                        break
                except Exception:
                    await page_worker.wait_for_timeout(1000)"""

if antigo in codigo:
    codigo = codigo.replace(antigo, novo, 1)
    with open("local_worker.py", "w", encoding="utf-8") as f:
        f.write(codigo)
    print("[OK] Resiliencia de navegacao aplicada com sucesso!")
else:
    print("[INFO] Trecho ja atualizado ou alterado.")
