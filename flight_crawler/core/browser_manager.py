from playwright.async_api import async_playwright, Playwright, Browser
from fake_useragent import UserAgent
import logging

class BrowserManager:
    def __init__(self):
        self.playwright: Playwright = None
        self.browser: Browser = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.ua = UserAgent()

    async def start(self):
        """
        Starts the Playwright engine and launches the browser.
        """
        if not self.playwright:
            self.playwright = await async_playwright().start()

        if not self.browser:
            # In a real scenario, we might launch multiple browsers or connect to a grid
            # For this standalone project, we launch one browser instance
            self.browser = await self.playwright.chromium.launch(
                headless=True, # Set to False for debugging
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--disable-http2',
                ]
            )
            self.logger.info("Browser launched")

    async def stop(self):
        """
        Stops the browser and Playwright engine.
        """
        if self.browser:
            await self.browser.close()
            self.browser = None

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            self.logger.info("Playwright stopped")

    async def get_new_context(self):
        """
        Creates a new browser context with randomized User-Agent and Proxy settings.
        """
        if not self.browser:
            await self.start()

        # Force a desktop User-Agent for consistent layout across all scrapers
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        # Proxy placeholder logic
        # proxy = {
        #     "server": "http://myproxy:8080",
        #     "username": "user",
        #     "password": "password"
        # }

        context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080},
            # proxy=proxy # Uncomment when proxy is available
        )

        self.logger.info(f"Created new context with UA: {user_agent}")
        return context
