from abc import ABC, abstractmethod
from typing import List, Optional
from playwright.async_api import Page, BrowserContext
from flight_crawler.core.models import FlightSearchInput, FlightResult
from flight_crawler.core.browser_manager import BrowserManager
import logging

class BaseScraper(ABC):
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self.logger = logging.getLogger(self.__class__.__name__)

    async def scrape(self, search_input: FlightSearchInput) -> List[FlightResult]:
        """
        Main entry point for scraping.
        """
        context = await self.browser_manager.get_new_context()
        page = await context.new_page()
        results = []
        try:
            await self._apply_stealth(page)
            results = await self._perform_search(page, search_input)
        except Exception as e:
            self.logger.error(f"Error during scrape: {e}")
            await self._handle_error(page, e)
        finally:
            await context.close()
        return results

    async def _apply_stealth(self, page: Page):
        """
        Apply stealth scripts to the page.
        """
        # Default implementation, can be overridden
        from flight_crawler.utils.stealth import inject_stealth
        await inject_stealth(page)

    @abstractmethod
    async def _perform_search(self, page: Page, search_input: FlightSearchInput) -> List[FlightResult]:
        """
        Concrete implementation of the search logic.
        """
        pass

    async def _handle_error(self, page: Page, error: Exception):
        """
        Handle errors (e.g., take screenshot, log).
        """
        # Placeholder for error handling logic
        pass
