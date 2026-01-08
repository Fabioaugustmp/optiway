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

        url = self._build_url(search_input)

        try:
            # Kayak has a "loading bar" logic
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # Anti-bot human behavior
            await self._simulate_human_behavior(page)

            # 4. DOM Scrape Fallback (Wait for results)
            results = []
            try:
                # Wait for any of the common card selectors
                await page.wait_for_selector('div.yuAt[role="group"]', timeout=30000)

                # Kayak renders results lazily, find all cards
                cards = await page.query_selector_all('div.yuAt[role="group"]')
                self.logger.info(f"Found {len(cards)} flight cards on Kayak")

                for card in cards:
                    try:
                        # Selectors found via browser agent
                        airline_el = await card.query_selector('.J0g6-operator-text, .J0g6-labels-grp div')
                        price_el = await card.query_selector('.e2GB-price-text, div[class*="price"]')

                        airline = await airline_el.inner_text() if airline_el else "Unknown Airline"
                        price_text = await price_el.inner_text() if price_el else "0"

                        # Clean price (e.g., "R$ 3.829\nLight" -> 3829.0)
                        # Take only the first line as it usually contains the price
                        price_val = price_text.split('\n')[0]
                        price_clean = price_val.replace("R$", "").replace("\xa0", "").replace(".", "").replace(",", ".").strip()
                        price = float(price_clean) if price_clean else 0.0

                        results.append(FlightResult(
                            airline=airline,
                            flight_number="N/A",
                            departure_time=datetime.now(),
                            arrival_time=datetime.now(),
                            price=price,
                            currency="BRL",
                            deep_link=page.url,
                            source_scraper="KayakScraper"
                        ))
                    except Exception as e:
                        self.logger.warning(f"Failed to parse Kayak card: {e}")

            except Exception as e:
                 self.logger.error(f"DOM scraping failed on Kayak: {e}")

            return results

        except Exception as e:
             self.logger.error(f"Navigation to Kayak failed: {e}")
             return []

    def _build_url(self, search_input: FlightSearchInput) -> str:
        # Using .com.br for better consistency with currency parsing
        base = "https://www.kayak.com.br/flights"

        route = f"{search_input.origin}-{search_input.destination}"
        dates = f"{search_input.departure_date}"

        if search_input.return_date:
            dates += f"/{search_input.return_date}"

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
