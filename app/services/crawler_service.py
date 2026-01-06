import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List
from app.schemas.travel import Flight, Hotel, CarRental

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

                flights.append(Flight(
                    origin=origin,
                    destination=dest,
                    price=round(price, 2),
                    duration_minutes=duration,
                    airline=airline,
                    departure_time=dep_time,
                    arrival_time=arr_time,
                    stops=0,
                    baggage="1 PC",
                    details=f"{origin}->{dest}"
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

    def fetch_car_rentals(self, cities: List[str]) -> List[CarRental]:
        # TODO: Implement Amadeus Car Search
        return []

    def _get_iata(self, city_name: str) -> str:
        mapping = {
            "São Paulo": "GRU", "Sao Paulo": "GRU",
            "Rio de Janeiro": "GIG",
            "Belo Horizonte": "CNF",
            "Brasília": "BSB", "Brasilia": "BSB",
            "Salvador": "SSA", "Curitiba": "CWB",
            "Florianópolis": "FLN", "Florianopolis": "FLN",
            "Miami": "MIA", "Orlando": "MCO",
            "New York": "JFK", "Chicago": "ORD",
            "Las Vegas": "LAS", "Los Angeles": "LAX", "San Francisco": "SFO",
            "Paris": "CDG", "London": "LHR"
        }
        return mapping.get(city_name, "GRU")

def get_crawler(provider: str = "Mock Data", key: str = None, secret: str = None) -> BaseCrawler:
    if provider == "Amadeus API" and key and secret:
        return AmadeusCrawler(key, secret)
    # Default to Mock
    return MockCrawler()
