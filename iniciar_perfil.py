import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def inicializar_perfil():
    async with async_playwright() as p:
        # Cria contexto persistente que salva cookies e cache no disco
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./perfil_ml",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        print("Abrindo Mercado Livre para registrar sessao...")
        await page.goto("https://lista.mercadolivre.com.br/fone", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        
        html = await page.content()
        await context.close()
        
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".poly-card, .ui-search-layout__item, div.ui-search-result__wrapper")
        print("=== STATUS DO PERFIL PERSISTENTE ===")
        print("Tamanho HTML:", len(html))
        print("Cards detectados:", len(cards))

asyncio.run(inicializar_perfil())
