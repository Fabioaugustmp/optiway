import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np
from data.models import Flight, Hotel, CarRental

# Try importing Selenium, but don't fail if not installed yet (for initial setup)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

class BaseCrawler(ABC):
    @abstractmethod
    @abstractmethod
    def fetch_flights(self, origin: str, destinations: List[str], date: datetime, adults: int = 1, children: int = 0) -> List[Flight]:
        pass

    @abstractmethod
    def fetch_hotels(self, cities: List[str]) -> List[Hotel]:
        pass

    @abstractmethod
    def fetch_car_rentals(self, cities: List[str]) -> List[CarRental]:
        pass

class MockCrawler(BaseCrawler):
    def fetch_flights(self, origin: str, destinations: List[str], date: datetime, adults: int = 1, children: int = 0) -> List[Flight]:
        flights = []
        for dest in destinations:
            if origin == dest:
                continue
            
            # Generate 3-5 flight options per route
            for _ in range(random.randint(3, 5)):
                price = random.uniform(200, 1500)
                duration = random.randint(45, 300) # minutes
                airline = random.choice(["Latam", "Gol", "Azul", "Voepass"])
                
                # Randomize dep time
                hour = random.randint(6, 22)
                minute = random.choice([0, 15, 30, 45])
                dep_time = date.replace(hour=hour, minute=minute)
                arr_time = dep_time + timedelta(minutes=duration)

                flight_no = f"{random.choice(['G3', 'LA', 'AD', '2Z'])}{random.randint(1000, 9999)}"

                flights.append(Flight(
                    origin=origin,
                    destination=dest,
                    price=round(price, 2),
                    duration_minutes=duration,
                    airline=airline,
                    departure_time=dep_time,
                    arrival_time=arr_time,
                    flight_number=flight_no
                ))
        return flights

    def fetch_hotels(self, cities: List[str]) -> List[Hotel]:
        hotels = []
        for city in cities:
            for i in range(random.randint(3, 6)):
                name = f"Hotel {random.choice(['Plaza', 'Royal', 'Suites', 'Inn', 'Grand'])} {city}"
                price = random.uniform(150, 800)
                rating = round(random.uniform(3.0, 5.0), 1)
                hotels.append(Hotel(city=city, name=name, price_per_night=round(price, 2), rating=rating))
        return hotels

    def fetch_car_rentals(self, cities: List[str]) -> List[CarRental]:
        cars = []
        for city in cities:
            for _ in range(random.randint(2, 4)):
                company = random.choice(["Localiza", "Movida", "Unidas"])
                model = random.choice(["Gol", "Onix", "Compass", "Renegade"])
                price = random.uniform(80, 250)
                cars.append(CarRental(city=city, company=company, price_per_day=round(price, 2), model=model))
        return cars

class GoogleFlightsCrawler(BaseCrawler):
    def __init__(self, headless=True):
        if not HAS_SELENIUM:
            raise ImportError("Selenium not installed.")
        
        self.options = Options()
        if headless:
            self.options.add_argument("--headless")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("--remote-allow-origins=*")
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option("useAutomationExtension", False)
        self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

    def _get_driver(self):
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)

    def fetch_flights(self, origin: str, destinations: List[str], date: datetime, adults: int = 1, children: int = 0) -> List[Flight]:
        flights = []
        driver = None
        try:
            driver = self._get_driver()
            
            for dest in destinations:
                if origin == dest:
                    continue
                
                # Construct URL using query mechanism which is more robust than direct URL hacking
                # Format: "Flights from [Origin] to [Dest] on [Date]"
                date_str = date.strftime("%Y-%m-%d")
                query = f"Flights from {origin} to {dest} on {date_str}"
                encoded_query = query.replace(" ", "+")
                url = f"https://www.google.com/travel/flights?q={encoded_query}"
                
                print(f"Crawling: {url}")
                driver.get(url)
                
                # Wait for results to load (Look for specific flights UI elements)
                # Google Flights usually puts listed flights in a role="listitem" or specific class
                try:
                    # Wait for at least one price element or flight card. Increased timeout to 30s as requested.
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'R$')] | //div[@role='listitem']"))
                    )
                except Exception:
                    print(f"Timeout waiting for results for {origin}->{dest} (30s). Attempting to parse whatever is visible...")
                    # Do not continue; proceed to parse what we have

                # Parse content
                from bs4 import BeautifulSoup
                import re
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Heuristic parsing for Google Flights standard result cards
                # Best effort to find the flight list items. usually a role='main' then lists.
                # We search for elements that contain price and duration.
                
                # Find all list items that might be flights
                # This is tricky as classes change. We look for 'li' elements in the main area.
                flight_cards = soup.find_all('li', class_=re.compile(r'pIav2d')) # Common class for flight cards in recent versions
                
                # Fallback if specific class not found
                if not flight_cards:
                    # Try finding by ARIA label or generic structure
                     flight_cards = soup.select('div[role="listitem"]') # Broad fallback logic

                count = 0 
                for card in flight_cards:
                    if count > 5: break # Limit to top 5 flights per route for speed
                    
                    try:
                        text_content = card.get_text(separator=" | ")
                        
                        # Extract Price (Handle BRL 1.234,56 format)
                        # Look for R$ followed by digits, dots and maybe comma
                        price_match = re.search(r'R\$\s?([\d\.]+),?(\d{2})?', text_content)
                        if not price_match: continue
                        
                        # raw: 1.234 or 1234
                        raw_int = price_match.group(1).replace('.', '')
                        cents = price_match.group(2) if price_match.group(2) else "00"
                        price = float(f"{raw_int}.{cents}")
                        
                        # Extract Duration
                        dur_match = re.search(r'(\d+)h\s?(\d+)?m?', text_content)
                        minutes = 0
                        if dur_match:
                            h = int(dur_match.group(1))
                            m = int(dur_match.group(2)) if dur_match.group(2) else 0
                            minutes = h * 60 + m
                        else:
                            minutes = 120 # Default fallback
                            
                        # Extract Airline (Heuristic: First few words usually, or look for specific known airlines)
                        airline = "Unknown"
                        for company in ["Latam", "Gol", "Azul", "Voepass", "American", "United", "Delta", "Air France"]:
                            if company in text_content:
                                airline = company
                                break
                        
                        # Times
                        # Simple heuristics for now
                        dep_time = date.replace(hour=8, minute=0) # Mock time if parsing fails
                        arr_time = dep_time + timedelta(minutes=minutes)

                        flights.append(Flight(
                            origin=origin,
                            destination=dest,
                            price=price,
                            duration_minutes=minutes,
                            airline=airline,
                            departure_time=dep_time,
                            arrival_time=arr_time
                        ))
                        print(f"[CRAWLER] Found: {airline} | {origin}->{dest} | R$ {price:.2f} | {minutes}min")
                        count += 1
                        
                    except Exception as e:
                        print(f"Error parsing card: {e}")
                        continue
                        
        except Exception as e:
            print(f"Crawler Error: {e}")
        finally:
            if driver:
                driver.quit()
                
        return flights

    def fetch_hotels(self, cities: List[str]) -> List[Hotel]:
        return []

    def fetch_car_rentals(self, cities: List[str]) -> List[CarRental]:
        return []

class AmadeusCrawler(BaseCrawler):
    def __init__(self, client_id: str, client_secret: str, production: bool = False):
        self.production = production
        self.client_id = client_id
        self.client_secret = client_secret
        
        # Verify Auth Manually (as requested to follow Manual)
        self.validate_auth()
        
        try:
            from amadeus import Client, ResponseError
            # Initialize Client (hostname='production' if selected, else default 'test')
            # Enable debug logging to see full request/response
            if production:
                self.amadeus = Client(
                    client_id=client_id,
                    client_secret=client_secret,
                    hostname='production',
                    log_level='debug'
                )
            else:
                # Explicitly set test environment
                self.amadeus = Client(
                    client_id=client_id,
                    client_secret=client_secret,
                    hostname='test',
                    log_level='debug'
                )
            self.client_ready = True
        except Exception as e:
            print(f"Amadeus Init Error: {e}")
            self.client_ready = False

    def validate_auth(self):
        """Manual implementation of Auth flow for debugging"""
        import requests
        
        base_url = "https://api.amadeus.com" if self.production else "https://test.api.amadeus.com"
        token_url = f"{base_url}/v1/security/oauth2/token"
        
        print(f"\n--- MANUAL AUTH CHECK ---")
        print(f"Target URL: {token_url}")
        
        try:
            response = requests.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("✅ TEST AUTH SUCCESSFUL! Token received.")
            else:
                print(f"❌ TEST AUTH FAILED: {response.text}")
                
        except Exception as e:
            print(f"❌ TEST AUTH ERROR: {e}")
        print(f"--- END MANUAL CHECK ---\n")

    def fetch_flights(self, origin: str, destinations: List[str], date: datetime, adults: int = 1, children: int = 0) -> List[Flight]:
        if not self.client_ready:
            print("Amadeus client not ready.")
            return []
            
        flights = []
        for dest in destinations:
            if origin == dest: continue
            
            try:
                date_str = date.strftime("%Y-%m-%d")
                cache_date_key = f"{date_str}_A{adults}_C{children}" # Update cache key
                
                # Check Cache First
                from data.database import FlightCache
                cache = FlightCache()
                cached_data = cache.get_cached_response(origin, dest, cache_date_key, "AMADEUS")
                
                response_data = None
                
                if cached_data:
                    print(f"[CACHE HIT] Using cached data for Amadeus {origin}->{dest}")
                    response_data = cached_data
                else:
                    # API Call
                    # Amadeus API supports 'children' and 'infants'
                    # We map our 'children' input to API 'children' (2-11yo)
                    # If we wanted to support infants, we would need another param.
                    
                    req_params = {
                        "originLocationCode": self._get_iata(origin),
                        "destinationLocationCode": self._get_iata(dest),
                        "departureDate": date_str,
                        "adults": adults,
                        "max": 25,
                        "currencyCode": 'BRL'
                    }
                    if children > 0:
                        req_params["children"] = children
                        
                    response = self.amadeus.shopping.flight_offers_search.get(**req_params)

                    if response.data:
                        response_data = response.data
                        # Save to Cache
                        cache.save_response(origin, dest, cache_date_key, response_data, "AMADEUS")
                
                if response_data:
                    for offer in response_data:
                        # Extract first segment details
                        itineraries = offer['itineraries'][0]
                        segment = itineraries['segments'][0]
                        
                        # Price
                        price_total = float(offer['price']['total'])
                        currency = offer['price']['currency']
                        
                        # Duration (ISO 8601 PT1H30M)
                        import isodate
                        duration = isodate.parse_duration(itineraries['duration'])
                        minutes = int(duration.total_seconds() / 60)
                        
                        # Airline
                        carrier_code = segment['carrierCode']
                        
                        dep_time = datetime.fromisoformat(segment['departure']['at'])
                        arr_time = datetime.fromisoformat(segment['arrival']['at'])
                        
                        # --- Enhanced Data Parsing ---
                        # Stops
                        segments = itineraries['segments']
                        stops = len(segments) - 1
                        
                        # Details string
                        seg_details = []
                        for s in segments:
                            flight_no = f"{s['carrierCode']}{s['number']}"
                            seg_str = f"{s['departure']['iataCode']}->{s['arrival']['iataCode']} ({flight_no})"
                            seg_details.append(seg_str)
                        details_str = ", ".join(seg_details)
                        
                        # Baggage
                        baggage_info = "N/A"
                        try:
                            first_traveler = offer['travelerPricings'][0]
                            first_seg_fare = first_traveler['fareDetailsBySegment'][0]
                            
                            if 'includedCheckedBags' in first_seg_fare:
                                bags = first_seg_fare['includedCheckedBags']
                                if 'quantity' in bags:
                                    baggage_info = f"{bags['quantity']} PC"
                                elif 'weight' in bags:
                                    baggage_info = f"{bags['weight']} {bags.get('weightUnit', 'KG')}"
                            else:
                                baggage_info = "0 PC" 
                        except Exception:
                            baggage_info = "?"
                        
                        flights.append(Flight(
                            origin=origin,
                            destination=dest,
                            price=price_total,
                            duration_minutes=minutes,
                            airline=carrier_code,
                            departure_time=dep_time,
                            arrival_time=arr_time,
                            stops=stops,
                            baggage=baggage_info,
                            details=details_str,
                            flight_number=f"{carrier_code}{segment['number']}"
                        ))
                        print(f"[AMADEUS] Found: {carrier_code} ({stops} stops) | {origin}->{dest} | {currency} {price_total}")
                        
            except Exception as e:
                # Catch specific connection errors
                if hasattr(e, 'response') and e.response:
                    print(f"Amadeus API Error for {origin}->{dest}: [{e.response.status_code}] {e.response.body}")
                else:
                    print(f"Amadeus API Error for {origin}->{dest}: {e}")
                
        return flights
    
    def fetch_hotels(self, cities: List[str]) -> List[Hotel]:
        if not self.client_ready:
            return []
            
        all_hotels = []
        from data.database import FlightCache
        cache = FlightCache()
        
        # Use a fixed date for generic hotel search cache
        cache_date = datetime.now().strftime("%Y-%m-%d")

        for city in cities:
            iata = self._get_iata(city)
            try:
                # Check Cache First
                cached_hotels_json = cache.get_cached_response(city, "HOTEL_SEARCH", cache_date, "AMADEUS_HOTEL")
                
                if cached_hotels_json:
                    print(f"[CACHE HIT] Using cached HOTEL data for {city}")
                    for h in cached_hotels_json:
                        all_hotels.append(Hotel(**h))
                    continue

                print(f"[AMADEUS] Fetching hotels for {city} ({iata})...")
                
                # Step 1: Get list of hotels in city
                hotels_response = self.amadeus.reference_data.locations.hotels.by_city.get(
                    cityCode=iata,
                    radius=5,
                    radiusUnit='KM'
                )
                
                if not hotels_response.data:
                    continue

                # Take top 10 hotels to check offers
                top_hotels = hotels_response.data[:10]
                hotel_ids = [h['hotelId'] for h in top_hotels]
                
                city_hotels = []
                # Step 2: Get Offers for these hotels
                for h_id in hotel_ids:
                    try:
                        offers_response = self.amadeus.shopping.hotel_offers_search.get(
                            hotelIds=h_id,
                            adults=1,
                            currency='BRL'
                        )
                        
                        if offers_response.data:
                            for offer in offers_response.data:
                                hotel_data = offer.get('hotel', {})
                                name = hotel_data.get('name', 'Unknown Hotel')
                                
                                offers = offer.get('offers', [])
                                if not offers: continue
                                
                                price = float(offers[0]['price']['total'])
                                
                                rating = hotel_data.get('rating')
                                try: rating = float(rating) if rating else 3.0
                                except: rating = 3.0

                                h_obj = Hotel(
                                    city=city,
                                    name=name,
                                    price_per_night=price,
                                    rating=rating
                                )
                                city_hotels.append(h_obj)
                                all_hotels.append(h_obj)
                    except Exception:
                        pass
                
                # Save city results to cache
                if city_hotels:
                    cache.save_response(
                        city, 
                        "HOTEL_SEARCH", 
                        cache_date, 
                        [h.__dict__ for h in city_hotels], 
                        "AMADEUS_HOTEL"
                    )

            except Exception as e:
                print(f"Amadeus Hotel Error for {city}: {e}")
                
        return all_hotels

    def fetch_car_rentals(self, cities: List[str]) -> List[CarRental]:
        if not self.client_ready:
            return []
            
        cars = []
        # Car Search in Amadeus usually requires a specific pick-up location (IATACode)
        # We will search for cars available at the airports of these cities.
        
        for city in cities:
            iata = self._get_iata(city)
            try:
                # Calculate pick-up date (tomorrow) to get generic availability
                start_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                end_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

                # NOTE: Amadeus has multiple Car APIs. 'shopping.transfer_offers' is for transfers.
                # 'shopping.availability.car_rentals' is for rental availability.
                # 'shopping.car_offers' is the older one? Let's try the modern 'availability' one if possible,
                # or rely on simple offers.
                # Based on common SDK versions:
                # response = self.amadeus.shopping.flight_offers_search.get(...)
                
                # Let's try flight_offers style but for cars.
                # Standard endpoint: shopping.availability.car_rentals
                
                # Check Cache for Cars
                from data.database import FlightCache
                cache = FlightCache()
                # Use a specific provider key for cars
                cache_key = f"{start_date}_{end_date}"
                cached_cars_json = cache.get_cached_response(city, "RENTAL_SEARCH", cache_key, "AMADEUS_CAR")
                
                response_data = None
                if cached_cars_json:
                     print(f"[CACHE HIT] Using cached CAR data for {city}")
                     response_data = cached_cars_json
                else:
                    print(f"[AMADEUS] Fetching cars for {city} ({iata})...")
                    # Using a broad search
                    response = self.amadeus.shopping.availability.city_search.get(
                        cityCode=iata,
                        start=f"{start_date}T10:00:00",
                        end=f"{end_date}T10:00:00"
                    )
                    if response.data:
                        response_data = response.data
                        cache.save_response(city, "RENTAL_SEARCH", cache_key, response_data, "AMADEUS_CAR")
                
                if response_data:
                    # Parse first few results
                    count = 0
                    for offer in response_data:
                        if count > 2: break
                        
                        provider = offer.get('provider', {}).get('companyName', 'Unknown')
                        # Price is often nested in vehicle details or 'estimatedTotal'
                        # Structure varies significantly.
                        # Mocking parsing logic for prototype safety if structure is complex,
                        # but attempting to grab price.
                        
                        vehicles = offer.get('vehicles', [])
                        if vehicles:
                            veh = vehicles[0]
                            price_info = veh.get('estimatedTotal', {})
                            amount = float(price_info.get('amount', 0.0))
                            currency = price_info.get('currency', 'BRL')
                            model = veh.get('category', 'Compact') # Simplified
                            
                            cars.append(CarRental(
                                city=city,
                                company=provider,
                                price_per_day=amount, # Assuming total is roughly 1 day cost here
                                model=model
                            ))
                            count += 1
                            print(f"[AMADEUS] Found Car: {provider} in {city} | {amount} {currency}")

            except Exception as e:
                # If API fails (e.g. not authorized for Cars), we catch it so the app doesn't crash
                # and flows back to default ground segment logic.
                # print(f"[AMADEUS] Car API Error/Skipped for {city}: {e}")
                pass

        return cars

    def _get_iata(self, city_name: str) -> str:
        # Simple Mock IATA Mapper or use Amadeus City Search
        # For prototype, we map common Brazilian cities
        mapping = {
            "São Paulo": "GRU", "Sao Paulo": "GRU",
            "Rio de Janeiro": "GIG",
            "Belo Horizonte": "CNF",
            "Brasília": "BSB", "Brasilia": "BSB",
            "Salvador": "SSA",
            "Curitiba": "CWB",
            "Florianópolis": "FLN", "Florianopolis": "FLN",
            "Miami": "MIA",
            "Orlando": "MCO",
            "New York": "JFK",
            "Paris": "CDG",
            "London": "LHR",
            "Uberlândia": "UDI",
            "Ituiutaba": "UDI",
            "Goiânia": "GYN", "Goiania": "GYN",
            "Aparecida de Goiânia": "GYN" # Fallback IATA for flight search if passed directly
        }
        return mapping.get(city_name, "GRU") # Default/Fallback
