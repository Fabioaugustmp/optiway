import asyncio
from playwright.async_api import async_playwright

async def debug_scrapers():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--disable-http2'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Test Azul
        print("Testing Azul...")
        try:
            url_azul = "https://www.voeazul.com.br/br/pt/home/selecao-voo?c[0].ds=GRU&c[0].as=JFK&c[0].dd=2026-05-20&p[0].t=ADT&p[0].c=1"
            await page.goto(url_azul, wait_until="networkidle", timeout=60000)
            await page.screenshot(path="debug_azul.png")
            print("Azul screenshot saved.")
        except Exception as e:
            print(f"Azul failed: {e}")
            
        # Test Latam
        print("Testing Latam...")
        try:
            url_latam = "https://www.latamairlines.com/br/pt/oferta-voos?origin=GRU&destination=JFK&outbound=2026-05-20T12:00:00.000Z&adults=1&trip=OW"
            await page.goto(url_latam, wait_until="networkidle", timeout=60000)
            await page.screenshot(path="debug_latam.png")
            print("Latam screenshot saved.")
        except Exception as e:
            print(f"Latam failed: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_scrapers())
