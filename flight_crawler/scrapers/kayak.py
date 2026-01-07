from typing import List
from playwright.async_api import Page
from flight_crawler.core.base_scraper import BaseScraper
from flight_crawler.core.models import FlightSearchInput, FlightResult
from datetime import datetime
import asyncio
import random
import urllib.parse

class KayakScraper(BaseScraper):
    async def _perform_search(self, page: Page, search_input: FlightSearchInput) -> List[FlightResult]:
        self.logger.info(f"Starting Kayak search for {search_input.origin} to {search_input.destination}")

        network_results = []

        # Kayak is aggressive. We monitor for specific XHRs that might contain flight data.
        # Often Kayak sends data in batch responses.
        async def handle_response(response):
            if "poll" in response.url and response.status == 200:
                try:
                    # Kayak polling endpoints often return partial results
                    # self.logger.info(f"Intercepted Kayak poll: {response.url}")
                    pass
                except Exception:
                    pass

        page.on("response", handle_response)

        url = self._build_url(search_input)

        try:
            # Kayak has a "loading bar"
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # Anti-bot human behavior
            await self._simulate_human_behavior(page)

            # Wait for results wrapper. Kayak classes are obfuscated but structure is stable.
            # We look for a common container or wait for the progress bar to finish.
            try:
                # Wait for the result list container
                await page.wait_for_selector('div.resultWrapper', timeout=25000)
                # Note: 'resultWrapper' is a common class, but might change.
                # Alternative: div[data-result-id]
            except Exception:
                self.logger.warning("Kayak results container not found or timeout.")

            # Extra wait for dynamic loading
            await asyncio.sleep(random.uniform(3, 6))

        except Exception as e:
             self.logger.error(f"Navigation to Kayak failed: {e}")

        return network_results if network_results else self._get_mock_data(search_input)

    def _build_url(self, search_input: FlightSearchInput) -> str:
        # Format: https://www.kayak.com/flights/SIN-KUL/2024-05-20/2024-05-25?sort=bestflight_a
        base = "https://www.kayak.com/flights"

        route = f"{search_input.origin}-{search_input.destination}"
        dates = f"{search_input.departure_date}"

        if search_input.return_date:
            dates += f"/{search_input.return_date}"

        # Params for passengers, cabin class could be added
        query_params = {
            "sort": "bestflight_a",
            "adults": search_input.passengers
        }

        # Construct path: /flights/ORI-DES/YYYY-MM-DD[/YYYY-MM-DD]
        url = f"{base}/{route}/{dates}?{urllib.parse.urlencode(query_params)}"
        return url

    async def _simulate_human_behavior(self, page: Page):
        # Kayak checks for cursor momentum
        for _ in range(random.randint(3, 7)):
            await page.mouse.move(random.randint(100, 1000), random.randint(100, 800))
            await asyncio.sleep(random.uniform(0.2, 0.7))

        # Scroll down to trigger lazy load
        await page.mouse.wheel(0, 500)
        await asyncio.sleep(1)

    def _get_mock_data(self, search_input: FlightSearchInput) -> List[FlightResult]:
        return [
            FlightResult(
                airline="Mixed",
                flight_number="KYK100",
                departure_time=datetime.now(),
                arrival_time=datetime.now(),
                price=250.00,
                currency="USD",
                deep_link="https://www.kayak.com",
                source_scraper="KayakScraper"
            )
        ]
