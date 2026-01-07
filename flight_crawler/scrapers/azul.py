from typing import List
from playwright.async_api import Page
from flight_crawler.core.base_scraper import BaseScraper
from flight_crawler.core.models import FlightSearchInput, FlightResult
from datetime import datetime
import asyncio
import random
import urllib.parse

class AzulScraper(BaseScraper):
    async def _perform_search(self, page: Page, search_input: FlightSearchInput) -> List[FlightResult]:
        self.logger.info(f"Starting Azul search for {search_input.origin} to {search_input.destination}")

        network_results = []

        async def handle_response(response):
            if "availability" in response.url and response.status == 200:
                try:
                    self.logger.info(f"Intercepted Azul availability: {response.url}")
                    # json_data = await response.json()
                    # parsed = self._parse_azul_response(json_data)
                    # network_results.extend(parsed)
                except Exception as e:
                    self.logger.debug(f"Failed to parse Azul response: {e}")

        page.on("response", handle_response)

        url = self._build_url(search_input)

        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(5)
            await self._simulate_human_behavior(page)

            try:
                # Wait for price elements
                await page.wait_for_selector('.flight-info', timeout=20000)
            except Exception:
                 self.logger.warning("Azul results container not found (timeout).")

        except Exception as e:
             self.logger.error(f"Navigation to Azul failed: {e}")

        return network_results if network_results else self._get_mock_data(search_input)

    def _build_url(self, search_input: FlightSearchInput) -> str:
        # Example: https://www.voeazul.com.br/br/pt/home/selecao-voo?c[0].ds=GRU&c[0].as=GIG&c[0].dd=2024-05-20&p[0].t=ADT&p[0].c=1
        base = "https://www.voeazul.com.br/br/pt/home/selecao-voo"

        # Azul URL parameters can be complex and change often.
        # Using a standard structure:
        params = {
            "c[0].ds": search_input.origin,
            "c[0].as": search_input.destination,
            "c[0].dd": search_input.departure_date, # YYYY-MM-DD
            "p[0].t": "ADT", # Adult
            "p[0].c": search_input.passengers
        }

        if search_input.return_date:
            # Round trip structure implies a second segment c[1] usually, but sometimes handled differently in URL
            # For simplicity in this POC, we focus on One Way or assume the site handles the initial param set for RT logic
            pass

        return f"{base}?{urllib.parse.urlencode(params)}"

    async def _simulate_human_behavior(self, page: Page):
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        await asyncio.sleep(random.uniform(1, 3))

    def _get_mock_data(self, search_input: FlightSearchInput) -> List[FlightResult]:
        return [
            FlightResult(
                airline="Azul",
                flight_number="AD4000",
                departure_time=datetime.now(),
                arrival_time=datetime.now(),
                price=400.00,
                currency="BRL",
                deep_link="https://www.voeazul.com.br",
                source_scraper="AzulScraper"
            )
        ]
