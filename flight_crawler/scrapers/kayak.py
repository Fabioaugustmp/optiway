from typing import List
from playwright.async_api import Page
from flight_crawler.core.base_scraper import BaseScraper
from flight_crawler.core.models import FlightSearchInput, FlightResult, CarSearchInput, CarResult
from datetime import datetime
import asyncio
import random
import urllib.parse

class KayakScraper(BaseScraper):
    async def _perform_search(self, page: Page, search_input: FlightSearchInput) -> List[FlightResult]:
        # ... existing flight search code ...
        self.logger.info(f"Starting Kayak search for {search_input.origin} to {search_input.destination}")

        url = self._build_url(search_input)

        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await self._simulate_human_behavior(page)

            results = []
            try:
                await page.wait_for_selector('div.yuAt[role="group"]', timeout=30000)
                cards = await page.query_selector_all('div.yuAt[role="group"]')
                self.logger.info(f"Found {len(cards)} flight cards on Kayak")

                for card in cards:
                    try:
                        airline_el = await card.query_selector('.J0g6-operator-text, .J0g6-labels-grp div')
                        price_el = await card.query_selector('.e2GB-price-text, div[class*="price"]')

                        airline = await airline_el.inner_text() if airline_el else "Unknown Airline"
                        price_text = await price_el.inner_text() if price_el else "0"

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

    async def _perform_car_search(self, page: Page, search_input: CarSearchInput) -> List[CarResult]:
        self.logger.info(f"Starting Kayak car search for {search_input.city}")
        
        # Simple slugification for city
        city_slug = search_input.city.replace(" ", "-")
        url = f"https://www.kayak.com.br/cars/{city_slug}/{search_input.pick_up_date}/{search_input.drop_off_date}?sort=rank_a"
        
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await self._simulate_human_behavior(page)
            
            results = []
            try:
                # Wait for car cards
                await page.wait_for_selector('div[class*="-content"], div.jo6g-content', timeout=30000)
                cards = await page.query_selector_all('div[class*="-content"], div.jo6g-content')
                self.logger.info(f"Found {len(cards)} car cards on Kayak")
                
                for card in cards:
                    try:
                        model_el = await card.query_selector('div[class*="title"], h3')
                        price_el = await card.query_selector('div[class*="price"], div[class*="Amount"]')
                        company_el = await card.query_selector('img[alt], div[class*="logo"], div[class*="Provider"]')
                        
                        if not model_el or not price_el:
                            continue
                            
                        model = await model_el.inner_text()
                        price_text = await price_el.inner_text()
                        
                        company = "Unknown"
                        if company_el:
                            tag = await company_el.evaluate("el => el.tagName")
                            if tag == 'IMG':
                                company = await company_el.get_attribute("alt")
                            else:
                                company = await company_el.inner_text()
                        
                        # Extract digits for price (Total price)
                        price_digits = "".join(filter(lambda c: c.isdigit() or c == ',', price_text.split('\n')[0]))
                        price_val = float(price_digits.replace(",", ".")) if price_digits else 0.0
                        
                        results.append(CarResult(
                            company=company.strip() if company else "Unknown",
                            model=model.strip(),
                            price=price_val,
                            deep_link=page.url,
                            source_scraper="KayakScraper"
                        ))
                    except Exception as e:
                        continue
            except Exception as e:
                self.logger.error(f"Car DOM scraping failed: {e}")
                
            return results
        except Exception as e:
            self.logger.error(f"Kayak car navigation failed: {e}")
            return []

    def _build_url(self, search_input: FlightSearchInput) -> str:
        base = "https://www.kayak.com.br/flights"
        route = f"{search_input.origin}-{search_input.destination}"
        dates = f"{search_input.departure_date}"
        if search_input.return_date:
            dates += f"/{search_input.return_date}"
        query_params = {"sort": "bestflight_a", "adults": search_input.passengers}
        return f"{base}/{route}/{dates}?{urllib.parse.urlencode(query_params)}"

    async def _simulate_human_behavior(self, page: Page):
        for _ in range(random.randint(2, 4)):
            await page.mouse.move(random.randint(100, 800), random.randint(100, 600))
            await asyncio.sleep(random.uniform(0.1, 0.3))
        await page.mouse.wheel(0, 400)
        await asyncio.sleep(0.5)
