import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List
from app.schemas.travel import Flight, Hotel, CarRental
from app.services.location_service import get_location_service

# Try importing Selenium
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
    def fetch_flights(self, origin: str, destinations: List[str], date: datetime, adults: int = 1, children: int = 0) -> List[Flight]:
        pass

    @abstractmethod
    def fetch_hotels(self, cities: List[str]) -> List[Hotel]:
        pass

    @abstractmethod
    def fetch_car_rentals(self, cities: List[str], date: datetime = None) -> List[CarRental]:
        pass


class AmadeusCrawler(BaseCrawler):
    def __init__(self, client_id: str, client_secret: str, production: bool = False):
        self.production = production
        self.client_id = client_id
        self.client_secret = client_secret
        self.client_ready = False

        try:
            from amadeus import Client
            hostname = 'production' if production else 'test'
            self.amadeus = Client(
                client_id=client_id,
                client_secret=client_secret,
                hostname=hostname,
                log_level='warn'
            )
            self.client_ready = True
        except Exception as e:
            print(f"Amadeus Init Error: {e}")

    def fetch_flights(self, origin: str, destinations: List[str], date: datetime, adults: int = 1, children: int = 0) -> List[Flight]:
        if not self.client_ready:
            return []

        flights = []
        for dest in destinations:
            if origin == dest: continue

            try:
                date_str = date.strftime("%Y-%m-%d")

                # Check Cache (To be implemented properly with DI, skipping for brevity or using direct DB access if needed)
                # For this Senior implementation, let's keep it simple: Real-time first.

                req_params = {
                    "originLocationCode": self._get_iata(origin),
                    "destinationLocationCode": self._get_iata(dest),
                    "departureDate": date_str,
                    "adults": adults,
                    "max": 10,
                    "currencyCode": 'BRL'
                }
                if children > 0:
                    req_params["children"] = children

                response = self.amadeus.shopping.flight_offers_search.get(**req_params)

                if response.data:
                    for offer in response.data:
                        itineraries = offer['itineraries'][0]
                        segment = itineraries['segments'][0]

                        price_total = float(offer['price']['total'])

                        import isodate
                        duration = isodate.parse_duration(itineraries['duration'])
                        minutes = int(duration.total_seconds() / 60)

                        carrier_code = segment['carrierCode']
                        dep_time = datetime.fromisoformat(segment['departure']['at'])
                        arr_time = datetime.fromisoformat(segment['arrival']['at'])

                        segments = itineraries['segments']
                        stops = len(segments) - 1

                        seg_details = []
                        for s in segments:
                            flight_no = f"{s['carrierCode']}{s['number']}"
                            seg_str = f"{s['departure']['iataCode']}->{s['arrival']['iataCode']} ({flight_no})"
                            seg_details.append(seg_str)
                        details_str = ", ".join(seg_details)

                        # Simplified baggage
                        baggage_info = "N/A"

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
                            details=details_str
                        ))
            except Exception as e:
                print(f"Amadeus Error {origin}->{dest}: {e}")

        return flights

    def fetch_hotels(self, cities: List[str]) -> List[Hotel]:
        if not self.client_ready:
            return []

        all_hotels = []
        
        for city in cities:
            try:
                iata = self._get_iata(city)
                
                # Step 1: Get list of hotels in city
                # Using reference-data/locations/hotels/by-city
                hotels_response = self.amadeus.reference_data.locations.hotels.by_city.get(
                    cityCode=iata,
                    radius=5,
                    radiusUnit='KM'
                )
                
                if not hotels_response.data:
                    continue

                # Take top 10 hotels to check offers (API limits usually exist)
                top_hotels = hotels_response.data[:10]
                hotel_ids = [h['hotelId'] for h in top_hotels]
                
                if not hotel_ids:
                    continue

                # Step 2: Get Offers for these hotels
                # Fetch individually to avoid batch failure if one ID is invalid (common Amadeus issue)
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
                                if not rating: rating = 3.0
                                else:
                                    try: rating = float(rating)
                                    except: rating = 3.0

                                all_hotels.append(Hotel(
                                    city=city,
                                    name=name,
                                    price_per_night=price,
                                    rating=rating
                                ))
                    except Exception as loop_e:
                        # Log specific hotel failure but continue
                        # print(f"Failed for hotel {h_id}: {loop_e}")
                        pass

            except Exception as e:
                print(f"Amadeus Hotel Error for {city}: {e}")
                if hasattr(e, 'response'):
                    try:
                        print(f"Amadeus Response: {e.response.body}")
                    except: pass
                pass
        
        return all_hotels

    def fetch_car_rentals(self, cities: List[str], date: datetime = None) -> List[CarRental]:
        # TODO: Implement Amadeus Car Search
        return []

    def _get_iata(self, city_name: str) -> str:
        return get_location_service().resolve_iata(city_name)

import requests
import logging

logger = logging.getLogger(__name__)

class FlightCrawlerProxy(BaseCrawler):
    """
    Proxy crawler that delegates flight searches to the flight-crawler microservice on port 8001.
    """
    def __init__(self, scraper_name: str):
        self.scraper_name = scraper_name.lower().replace(" ", "_")
        self.base_url = "http://localhost:8001/api/v1/crawl"

    def fetch_flights(self, origin: str, destinations: List[str], date: datetime, adults: int = 1, children: int = 0) -> List[Flight]:
        try:
            search_inputs = []
            origin_iata = self._get_iata(origin)
            
            for dest in destinations:
                dest_iata = self._get_iata(dest)
                search_inputs.append({
                    "origin": origin_iata,
                    "destination": dest_iata,
                    "departure_date": date.strftime("%Y-%m-%d"),
                    "passengers": adults + children,
                    "scrapers": [self.scraper_name]
                })

            response = requests.post(self.base_url, json=search_inputs, timeout=120)
            response.raise_for_status()
            
            result_data = response.json()
            if result_data.get("status") != "success":
                logger.error(f"FlightCrawler error: {result_data}")
                return []

            flights = []
            results = result_data.get("data", {})
            scraper_key = self.scraper_name
            if scraper_key not in results:
                scraper_key = next((k for k in results.keys() if self.scraper_name in k.lower()), None)

            if scraper_key and scraper_key in results:
                for f in results[scraper_key]:
                    flights.append(Flight(
                        origin=origin,
                        destination=f.get("destination_name", destinations[0]), 
                        price=float(f.get("price", 0)),
                        duration_minutes=int(f.get("duration_minutes", 0)) or 180,
                        airline=f.get("airline", "N/A"),
                        departure_time=datetime.fromisoformat(f.get("departure_time")),
                        arrival_time=datetime.fromisoformat(f.get("arrival_time")),
                        stops=f.get("stops", 0),
                        baggage=f.get("baggage", "N/A"),
                        flight_number=f.get("flight_number", "N/A"),
                        details=f.get("deep_link", ""),
                        deep_link=f.get("deep_link", "")
                    ))
            
            return flights
        except Exception as e:
            logger.error(f"Error calling FlightCrawler for {self.scraper_name}: {e}")
            return []

    def _get_iata(self, city_name: str) -> str:
        return get_location_service().resolve_iata(city_name)

    def fetch_hotels(self, cities: List[str]) -> List[Hotel]:
        return []

    def fetch_car_rentals(self, cities: List[str], date: datetime = None) -> List[CarRental]:
        """Fetch car rentals from the microservice."""
        if self.scraper_name != "kayak":
            return []
            
        try:
            # Use provided date or fallback to 30 days from now
            start = date if date else (datetime.now() + timedelta(days=30))
            end = start + timedelta(days=2)
            
            search_inputs = []
            for city in cities:
                search_inputs.append({
                    "city": city,
                    "pick_up_date": start.strftime("%Y-%m-%d"),
                    "drop_off_date": end.strftime("%Y-%m-%d"),
                    "scrapers": ["kayak"]
                })

            response = requests.post("http://localhost:8001/api/v1/crawl-cars", json=search_inputs, timeout=120)
            response.raise_for_status()
            
            result_data = response.json()
            if result_data.get("status") != "success":
                return []

            cars = []
            results = result_data.get("data", {})
            for scraper_key, car_list in results.items():
                for c in car_list:
                    cars.append(CarRental(
                        city=c.get("city") or cities[0],
                        company=c.get("company"),
                        price_per_day=float(c.get("price", 0)) / 2, # Assuming 2-day search
                        model=c.get("model"),
                        deep_link=c.get("deep_link", "")
                    ))
            return cars
        except Exception as e:
            logger.error(f"Error calling FlightCrawler for cars: {e}")
            return []

def get_crawler(provider: str = "Kayak", key: str = None, secret: str = None) -> BaseCrawler:
    if provider == "Amadeus API" and key and secret:
        return AmadeusCrawler(key, secret)
    elif provider in ["Kayak", "Google Flights"]:
        return FlightCrawlerProxy(provider)
    
    raise ValueError(f"Provider '{provider}' not supported or not configured.")
