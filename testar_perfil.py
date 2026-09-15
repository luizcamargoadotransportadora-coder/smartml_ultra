import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def registrar_sessao():
    async with async_playwright() as p:
        # Abre o navegador salvando dados e cookies na pasta perfil_ml
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./perfil_ml",
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        print("Acessando Mercado Livre...")
        await page.goto("https://lista.mercadolivre.com.br/fone", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(4000)
        
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".poly-card, .ui-search-layout__item, div.ui-search-result__wrapper")
        
        print("=== STATUS DO TESTE COM PERFIL ===")
        print("Tamanho HTML:", len(html))
        print("Cards detectados:", len(cards))
        
        await context.close()

asyncio.run(registrar_sessao())
