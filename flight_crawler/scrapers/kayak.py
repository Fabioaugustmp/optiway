from typing import List
from playwright.async_api import Page
from flight_crawler.core.base_scraper import BaseScraper
from flight_crawler.core.models import (
    FlightSearchInput, FlightResult, 
    CarSearchInput, CarResult,
    HotelSearchInput, HotelResult
)
from datetime import datetime, timedelta
import asyncio
import random
import urllib.parse
import re


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
                # Wait for flight cards
                # Try multiple common selectors for Kayak flight results
                await page.wait_for_selector('div.yuAt[role="group"], div[class*="resultWrapper"], div[class*="Result"], div.nrc6', timeout=30000)
                
                # Query all potential cards
                # Use stricter selectors to avoid ads
                cards = await page.query_selector_all('div.nrc6, div.yuAt[role="group"], div.ResultCard')
                if not cards:
                     # Fallback to resultWrapper but check for specific inner elements that imply a flight
                     potential_cards = await page.query_selector_all('div[class*="resultWrapper"]')
                     cards = []
                     for p_card in potential_cards:
                         if await p_card.query_selector('div[class*="section"]'):
                             cards.append(p_card)

                self.logger.info(f"Found {len(cards)} potential flight cards on Kayak")

                for card in cards:
                    try:
                        airline_el = await card.query_selector('.J0g6-operator-text, .J0g6-labels-grp div, div[class*="name"]')
                        # Price Extraction
                        # Try multiple selectors for price (case insensitive coverage)
                        price_el = await card.query_selector('.f8F1-price-text, .e2GB-price-text, div[class*="price-text"], span[class*="price"], div[class*="Price"], span[class*="Price"]')
                        
                        if not price_el:
                            # Fallback to broader search but avoid buttons
                            price_el = await card.query_selector('div[class*="price"]')
                        
                        if not price_el:
                            # Skip if no price (likely an ad)
                            continue
                        
                        airline = await airline_el.inner_text() if airline_el else "Unknown Airline"
                        price_text = await price_el.inner_text()
                        
                        # Extract digits using regex
                        price_matches = re.findall(r'(\d+[.,]?\d*)', price_text)
                        price = 0.0
                        if price_matches:
                             raw_price = price_matches[0]
                             clean_price = raw_price.replace('.', '').replace(',', '.')
                             try:
                                 price = float(clean_price)
                             except:
                                 pass

                        # Time Extraction Logic
                        times_el = await card.query_selector_all('span[class*="time"], div[class*="time"], div[class*="Time"], span[class*="Time"]')
                        # Helper to parse time
                        found_times = []
                        for t_el in times_el:
                            txt = await t_el.inner_text()
                            matches = re.findall(r'\b\d{1,2}[:h]\d{2}\b', txt)
                            found_times.extend(matches)
                            if len(found_times) >= 2: break
                        
                        dep_time_obj = None
                        arr_time_obj = None

                        if len(found_times) >= 2:
                            dep_str = found_times[0].replace('h', ':')
                            arr_str = found_times[1].replace('h', ':')
                        else:
                            # Try larger text
                            card_text = await card.inner_text()
                            matches = re.findall(r'\b\d{1,2}[:h]\d{2}\b', card_text)
                            if len(matches) >= 2:
                                dep_str = matches[0].replace('h', ':')
                                arr_str = matches[1].replace('h', ':')
                            else:
                                # Skip if no times found (likely an ad)
                                continue

                        # Parse Dates
                        base_date = search_input.departure_date
                        if isinstance(base_date, str):
                            base_date = datetime.strptime(base_date, "%Y-%m-%d").date()
                        
                        dep_time_obj = datetime.combine(base_date, datetime.strptime(dep_str, "%H:%M").time())
                        arr_time_obj = datetime.combine(base_date, datetime.strptime(arr_str, "%H:%M").time())
                        
                        if arr_time_obj < dep_time_obj:
                                arr_time_obj += timedelta(days=1)

                        results.append(FlightResult(
                            origin=search_input.origin,
                            destination=search_input.destination,
                            airline=airline,
                            flight_number="N/A",
                            departure_time=dep_time_obj,
                            arrival_time=arr_time_obj,
                            price=price,
                            currency="BRL",
                            deep_link=page.url,
                            source_scraper="KayakScraper"
                        ))
                        # Limit to reasonable number of results
                        if len(results) >= 30: break
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

    async def _perform_hotel_search(self, page: Page, search_input: HotelSearchInput) -> List[HotelResult]:
        """
        Scrape hotel listings from Kayak.
        """
        self.logger.info(f"Starting Kayak hotel search for {search_input.city}")
        
        # Build Kayak hotel URL
        # Format: https://www.kayak.com.br/hotels/City/2026-02-01/2026-02-03/2adults?sort=rank_a
        city_slug = search_input.city.replace(" ", "-")
        guests_str = f"{search_input.guests}adults" if search_input.guests > 0 else "2adults"
        if search_input.rooms > 1:
            guests_str += f"/{search_input.rooms}rooms"
        
        url = f"https://www.kayak.com.br/hotels/{city_slug}/{search_input.check_in_date}/{search_input.check_out_date}/{guests_str}?sort=rank_a"
        self.logger.info(f"Navigating to: {url}")
        
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await self._simulate_human_behavior(page)
            
            # Wait for page to load more content
            await asyncio.sleep(3)
            
            # Scroll to load more results
            for _ in range(3):
                await page.mouse.wheel(0, 500)
                await asyncio.sleep(1)
            
            results = []
            try:
                # Wait for hotel cards to appear
                # Kayak hotel cards typically have class patterns like 'yuAt' or specific hotel result classes
                await page.wait_for_selector('div[data-resultid], div.yuAt, div[class*="result"]', timeout=30000)
                
                # Try multiple selectors for hotel cards
                cards = await page.query_selector_all('div[data-resultid]')
                if not cards:
                    cards = await page.query_selector_all('div.yuAt[role="group"]')
                if not cards:
                    cards = await page.query_selector_all('div[class*="HotelResult"], div[class*="hotel-result"]')
                
                self.logger.info(f"Found {len(cards)} hotel cards on Kayak")
                
                # Calculate number of nights for price per night calculation
                try:
                    check_in = datetime.strptime(search_input.check_in_date, "%Y-%m-%d")
                    check_out = datetime.strptime(search_input.check_out_date, "%Y-%m-%d")
                    num_nights = (check_out - check_in).days
                    if num_nights <= 0:
                        num_nights = 1
                except:
                    num_nights = 1
                
                for card in cards[:20]:  # Limit to 20 hotels
                    try:
                        # Extract hotel name
                        name_el = await card.query_selector('a[class*="name"], div[class*="name"], h3, span[class*="hotelName"]')
                        if not name_el:
                            name_el = await card.query_selector('a[aria-label], div[aria-label]')
                        
                        name = "Unknown Hotel"
                        if name_el:
                            name = await name_el.inner_text()
                            if not name.strip():
                                name = await name_el.get_attribute("aria-label") or "Unknown Hotel"
                        name = name.strip().split('\n')[0]  # Get first line if multiline
                        
                        # Extract price
                        price_el = await card.query_selector('div[class*="price"], span[class*="price"], div[class*="Price"]')
                        total_price = 0.0
                        if price_el:
                            price_text = await price_el.inner_text()
                            # Extract numbers from price text (e.g., "R$ 450" -> 450)
                            price_digits = re.sub(r'[^\d,.]', '', price_text.replace('.', '').replace(',', '.'))
                            if price_digits:
                                try:
                                    total_price = float(price_digits)
                                except ValueError:
                                    pass
                        
                        if total_price == 0:
                            # Try getting price from card text
                            card_text = await card.inner_text()
                            price_matches = re.findall(r'R\$\s*([\d.,]+)', card_text)
                            if price_matches:
                                try:
                                    total_price = float(price_matches[0].replace('.', '').replace(',', '.'))
                                except:
                                    pass
                        
                        price_per_night = total_price / num_nights if num_nights > 0 else total_price
                        
                        # Extract rating (e.g., "8.5/10" or "Excelente 8.5")
                        rating = None
                        rating_el = await card.query_selector('div[class*="rating"], span[class*="rating"], div[class*="score"]')
                        if rating_el:
                            rating_text = await rating_el.inner_text()
                            rating_matches = re.findall(r'(\d+[.,]?\d*)', rating_text)
                            if rating_matches:
                                try:
                                    rating = float(rating_matches[0].replace(',', '.'))
                                    # Normalize rating to 0-5 scale if it's on 0-10 scale
                                    if rating > 5:
                                        rating = rating / 2
                                except:
                                    pass
                        
                        # Extract stars (hotel category)
                        stars = None
                        stars_el = await card.query_selector('div[class*="stars"], span[class*="stars"], div[class*="Stars"]')
                        if stars_el:
                            stars_text = await stars_el.inner_text()
                            stars_match = re.search(r'(\d)', stars_text)
                            if stars_match:
                                stars = int(stars_match.group(1))
                        
                        # Only add if we have at least a name
                        if name and name != "Unknown Hotel":
                            results.append(HotelResult(
                                name=name,
                                city=search_input.city,
                                price_per_night=round(price_per_night, 2),
                                total_price=round(total_price, 2),
                                rating=rating,
                                stars=stars,
                                currency="BRL",
                                deep_link=page.url,
                                source_scraper="KayakScraper",
                                amenities=None  # Could be extracted if needed
                            ))
                    except Exception as e:
                        self.logger.warning(f"Failed to parse hotel card: {e}")
                        continue
                        
            except Exception as e:
                self.logger.error(f"Hotel DOM scraping failed: {e}")
            
            self.logger.info(f"Successfully scraped {len(results)} hotels")
            return results
            
        except Exception as e:
            self.logger.error(f"Kayak hotel navigation failed: {e}")
            return []
