import asyncio
from typing import List, Dict
from flight_crawler.core.browser_manager import BrowserManager
from flight_crawler.scrapers.google_flights import GoogleFlightsScraper
from flight_crawler.scrapers.latam import LatamScraper
from flight_crawler.scrapers.azul import AzulScraper
from flight_crawler.scrapers.gol import GolScraper
from flight_crawler.scrapers.kayak import KayakScraper
from flight_crawler.core.models import FlightSearchInput, FlightResult
import logging

class CrawlerService:
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.scrapers = {
            "google_flights": GoogleFlightsScraper(self.browser_manager),
            "latam": LatamScraper(self.browser_manager),
            "azul": AzulScraper(self.browser_manager),
            "gol": GolScraper(self.browser_manager),
            "kayak": KayakScraper(self.browser_manager)
        }
        self.logger = logging.getLogger(self.__class__.__name__)

    async def crawl(self, search_inputs: List[FlightSearchInput]) -> Dict[str, List[FlightResult]]:
        """
        Orchestrates the scraping process across multiple inputs and scrapers.
        """
        results = {}

        # In a real system, we'd use a more robust queue/worker system (Celery/RabbitMQ)
        # For this standalone POC, we use asyncio.gather for concurrency.

        tasks = []
        for input_data in search_inputs:
            for scraper_name, scraper in self.scrapers.items():
                tasks.append(self._safe_scrape(scraper_name, scraper, input_data))

        # Execute all scraping tasks concurrently
        # Note: We need to manage the BrowserManager lifecycle.
        await self.browser_manager.start()

        try:
            completed_tasks = await asyncio.gather(*tasks)

            # Aggregate results
            for scraper_name, flight_results in completed_tasks:
                if scraper_name not in results:
                    results[scraper_name] = []
                results[scraper_name].extend(flight_results)

        finally:
            await self.browser_manager.stop()

        return results

    async def _safe_scrape(self, name, scraper, input_data) -> tuple:
        try:
            data = await scraper.scrape(input_data)
            return (name, data)
        except Exception as e:
            self.logger.error(f"Scraper {name} failed: {e}")
            return (name, [])
