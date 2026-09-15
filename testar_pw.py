import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def testar():
    async with async_playwright() as p:
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars"
        ]
        
        # Tenta usar o Chrome real instalado na máquina
        try:
            browser = await p.chromium.launch(headless=True, channel="chrome", args=args)
        except:
            browser = await p.chromium.launch(headless=True, args=args)
            
        context = await browser.new_context(
            locale="pt-BR",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        page = await context.new_page()
        
        # Oculta a variavel que denuncia o navegador automatizado
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        await page.goto("https://lista.mercadolivre.com.br/fone", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)
        
        html = await page.content()
        await browser.close()
        
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".poly-card, .ui-search-layout__item, div.ui-search-result__wrapper")
        print("=== RESULTADO PLAYWRIGHT STEALTH ===")
        print("Tamanho HTML:", len(html))
        print("Cards detectados:", len(cards))

asyncio.run(testar())
