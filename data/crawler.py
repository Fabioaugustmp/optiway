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
    def fetch_flights(self, origin: str, destinations: List[str], date: datetime) -> List[Flight]:
        pass

    @abstractmethod
    def fetch_hotels(self, cities: List[str]) -> List[Hotel]:
        pass

    @abstractmethod
    def fetch_car_rentals(self, cities: List[str]) -> List[CarRental]:
        pass

class MockCrawler(BaseCrawler):
    def fetch_flights(self, origin: str, destinations: List[str], date: datetime) -> List[Flight]:
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
                    arrival_time=arr_time
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
        self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    def _get_driver(self):
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)

    def fetch_flights(self, origin: str, destinations: List[str], date: datetime) -> List[Flight]:
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
                    # Wait for at least one price element or flight card
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'R$')]"))
                    )
                except Exception:
                    print(f"Timeout waiting for results for {origin}->{dest}")
                    continue

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
