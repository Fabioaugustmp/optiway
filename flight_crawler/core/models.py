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
    airline: str
    flight_number: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    currency: str = "USD"
    deep_link: str
    source_scraper: str
