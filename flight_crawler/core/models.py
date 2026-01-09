from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class FlightSearchInput(BaseModel):
    origin: str
    destination: str
    departure_date: str # YYYY-MM-DD
    return_date: Optional[str] = None
    passengers: int = 1
    scrapers: Optional[List[str]] = Field(default=None, description="List of scrapers to use (e.g., ['google_flights', 'latam'])")

class FlightResult(BaseModel):
    origin: str
    destination: str
    airline: str
    flight_number: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    currency: str = "USD"
    deep_link: str
    source_scraper: str

class CarSearchInput(BaseModel):
    city: str
    pick_up_date: str # YYYY-MM-DD
    drop_off_date: str # YYYY-MM-DD
    scrapers: Optional[List[str]] = Field(default=None)

class CarResult(BaseModel):
    company: str
    model: str
    price: float
    currency: str = "BRL"
    deep_link: str
    source_scraper: str

class HotelSearchInput(BaseModel):
    city: str
    check_in_date: str  # YYYY-MM-DD
    check_out_date: str  # YYYY-MM-DD
    guests: int = 2
    rooms: int = 1
    scrapers: Optional[List[str]] = Field(default=None)

class HotelResult(BaseModel):
    name: str
    city: str
    price_per_night: float
    total_price: float
    rating: Optional[float] = None
    stars: Optional[int] = None
    currency: str = "BRL"
    deep_link: str
    source_scraper: str
    amenities: Optional[List[str]] = None
