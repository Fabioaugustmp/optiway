from typing import List
from playwright.async_api import Page, Request
from flight_crawler.core.base_scraper import BaseScraper
from flight_crawler.core.models import FlightSearchInput, FlightResult
from datetime import datetime
import asyncio
import random
import json

class GoogleFlightsScraper(BaseScraper):
    async def _perform_search(self, page: Page, search_input: FlightSearchInput) -> List[FlightResult]:
        self.logger.info(f"Starting Google Flights search for {search_input.origin} to {search_input.destination}")

        # 1. Setup Network Interception (Hybrid Strategy)
        network_results = []
        results = []
        async def handle_response(response):
            if "batchelor" in response.url or "GetShoppingResults" in response.url: # Common GF patterns
                 try:
                     # This is a simplification. Google uses Protobuf/JSON arrays.
                     # In a real impl, we would decode the messy array.
                     # For this example, we log interception.
                     self.logger.info(f"Intercepted potential flight data from: {response.url}")
                     # text = await response.text()
                     # parsed = self._parse_google_json(text)
                     # network_results.extend(parsed)
                 except Exception as e:
                     self.logger.debug(f"Failed to parse network response: {e}")

        page.on("response", handle_response)

        # 2. Navigate
        url = self._build_url(search_input)
        await page.goto(url, wait_until="domcontentloaded")

        # 3. Random Human Interaction
        await self._simulate_human_behavior(page)

        # 4. DOM Scrape Fallback (Wait for results)
        try:
            # Wait for grid or list of flights
            await page.wait_for_selector('li.pIav2d', timeout=20000)

            flight_elements = await page.query_selector_all('li.pIav2d')
            self.logger.info(f"Found {len(flight_elements)} flight elements on Google Flights")

            for el in flight_elements:
                try:
                    # Robust extraction using JS to find elements by content if classes fail
                    airline = await el.evaluate("""el => {
                        const operator = el.querySelector('.Ir0Voe span, .sSHqwe.tPgKwe.ogfYpf span, .X8709b span');
                        if (operator) return operator.innerText;
                        // Fallback: look for typical airline name positions
                        return el.innerText.split('\\n')[1] || "Unknown";
                    }""")

                    price_text = await el.evaluate("""el => {
                        const price = el.querySelector('span[role="text"][aria-label*="Reais"], .YMlIz.FpEdX.jLMuyc span');
                        if (price) return price.innerText;
                        // Fallback: search for R$ in all spans
                        const spans = Array.from(el.querySelectorAll('span'));
                        const priceSpan = spans.find(s => s.innerText.includes('R$'));
                        return priceSpan ? priceSpan.innerText : "0";
                    }""")

                    # Basic price parsing (e.g., "R$ 3.829" -> 3829.0)
                    price_val = price_text.split('\n')[0]
                    price_clean = price_val.replace("R$", "").replace(".", "").replace(",", ".").replace("\xa0", "").strip()
                    price = float(price_clean) if price_clean else 0.0

                    # Use provided dates as base for datetime objects (times are usually "HH:MM")
                    # Note: Simplified datetime conversion for POC
                    base_date = search_input.departure_date
                    results.append(FlightResult(
                        airline=airline,
                        flight_number="N/A", # Often not directly in the main list
                        departure_time=datetime.now(), # Placeholder for actual parsing
                        arrival_time=datetime.now(), # Placeholder for actual parsing
                        price=price,
                        currency="BRL",
                        deep_link=page.url,
                        source_scraper="GoogleFlightsScraper"
                    ))
                except Exception as e:
                    self.logger.warning(f"Failed to parse individual flight: {e}")

            if not results and not network_results:
                 self.logger.warning("No flight elements successfully parsed via DOM.")
                 return []

        except Exception as e:
            self.logger.error(f"DOM scraping failed: {e}")

        return results if results else []

    def _build_url(self, search_input: FlightSearchInput) -> str:
        # https://www.google.com/travel/flights?q=Flights%20to%20JFK%20from%20LHR%20on%202024-05-20
        # Simplistic URL construction
        base = "https://www.google.com/travel/flights"
        query = f"Flights to {search_input.destination} from {search_input.origin} on {search_input.departure_date}"
        return f"{base}?q={query}"

    async def _simulate_human_behavior(self, page: Page):
        # Mouse movements
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.5))

        # Random scroll
        await page.mouse.wheel(0, random.randint(100, 500))
        await asyncio.sleep(random.uniform(0.5, 1.5))


