import asyncio
from typing import List, Dict
from flight_crawler.core.browser_manager import BrowserManager
from flight_crawler.scrapers.google_flights import GoogleFlightsScraper
from flight_crawler.scrapers.latam import LatamScraper
from flight_crawler.scrapers.azul import AzulScraper
from flight_crawler.scrapers.gol import GolScraper
from flight_crawler.scrapers.kayak import KayakScraper
from flight_crawler.core.models import FlightSearchInput, FlightResult, CarSearchInput, CarResult
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
        tasks = []
        for input_data in search_inputs:
            selected_scrapers = input_data.scrapers if input_data.scrapers else list(self.scrapers.keys())
            for scraper_name in selected_scrapers:
                if scraper_name in self.scrapers:
                    tasks.append(self._safe_scrape(scraper_name, self.scrapers[scraper_name], input_data))
                else:
                    self.logger.warning(f"Scraper '{scraper_name}' not found.")

        await self.browser_manager.start()
        try:
            completed_tasks = await asyncio.gather(*tasks)
            for scraper_name, flight_results in completed_tasks:
                if scraper_name not in results:
                    results[scraper_name] = []
                results[scraper_name].extend(flight_results)
        finally:
            await self.browser_manager.stop()
        return results

    async def crawl_cars(self, search_inputs: List[CarSearchInput]) -> Dict[str, List[CarResult]]:
        """
        Orchestrates the scraping process for car rentals.
        """
        results = {}
        tasks = []
        for input_data in search_inputs:
            # For now, only Kayak supports cars
            selected_scrapers = input_data.scrapers if input_data.scrapers else ["kayak"]
            for scraper_name in selected_scrapers:
                if scraper_name in self.scrapers:
                    tasks.append(self._safe_scrape_cars(scraper_name, self.scrapers[scraper_name], input_data))
        
        await self.browser_manager.start()
        try:
            completed_tasks = await asyncio.gather(*tasks)
            for scraper_name, car_results in completed_tasks:
                if scraper_name not in results:
                    results[scraper_name] = []
                results[scraper_name].extend(car_results)
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

    async def _safe_scrape_cars(self, name, scraper, input_data) -> tuple:
        try:
            data = await scraper.scrape_cars(input_data)
            return (name, data)
        except Exception as e:
            self.logger.error(f"Car Scraper {name} failed: {e}")
            return (name, [])
