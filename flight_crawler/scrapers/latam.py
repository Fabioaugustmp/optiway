from typing import List
from playwright.async_api import Page
from flight_crawler.core.base_scraper import BaseScraper
from flight_crawler.core.models import FlightSearchInput, FlightResult
from datetime import datetime
import asyncio
import random
import urllib.parse

class LatamScraper(BaseScraper):
    async def _perform_search(self, page: Page, search_input: FlightSearchInput) -> List[FlightResult]:
        self.logger.info(f"Starting LATAM search for {search_input.origin} to {search_input.destination}")

        network_results = []

        async def handle_response(response):
            # LATAM often uses specific API endpoints for flight data
            # Adjust filter as needed based on current API endpoints
            if "offers" in response.url and response.status == 200:
                try:
                    self.logger.info(f"Intercepted LATAM offers: {response.url}")
                    # json_data = await response.json()
                    # parsed = self._parse_latam_response(json_data)
                    # network_results.extend(parsed)
                except Exception as e:
                    self.logger.debug(f"Failed to parse LATAM response: {e}")

        page.on("response", handle_response)

        url = self._build_url(search_input)

        try:
            # LATAM can be slow to load
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # Simulate waiting for the SPA to hydrate
            await asyncio.sleep(5)
            await self._simulate_human_behavior(page)

            # Wait for results container
            try:
                # Common wrapper for results
                await page.wait_for_selector('div[id="WrapperCardFlight0"]', timeout=20000)
            except Exception:
                self.logger.warning("LATAM results container not found (timeout).")

        except Exception as e:
             self.logger.error(f"Navigation to LATAM failed: {e}")

        return network_results if network_results else []

    def _build_url(self, search_input: FlightSearchInput) -> str:
        # Example URL: https://www.latamairlines.com/br/pt/oferta-voos?origin=GRU&destination=GIG&outbound=2024-05-20&adults=1&trip=OW
        # Note: Date format usually YYYY-MM-DD
        base = "https://www.latamairlines.com/br/pt/oferta-voos"
        params = {
            "origin": search_input.origin,
            "destination": search_input.destination,
            "outbound": f"{search_input.departure_date}T12:00:00.000Z", # Often requires ISO format
            "adults": search_input.passengers,
            "trip": "OW" # One Way
        }
        if search_input.return_date:
            params["inbound"] = search_input.return_date
            params["trip"] = "RT"

        return f"{base}?{urllib.parse.urlencode(params)}"

    async def _simulate_human_behavior(self, page: Page):
        # Basic human-like jitter
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        await asyncio.sleep(random.uniform(1, 3))


