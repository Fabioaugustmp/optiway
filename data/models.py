from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class Flight:
    origin: str
    destination: str
    price: float
    duration_minutes: int
    airline: str
    departure_time: datetime
    arrival_time: datetime
    stops: int = 0
    baggage: str = "N/A"
    details: str = "" # e.g. "GRU->MIA (JJ123)"

    @property
    def formatted_price(self):
        return f"R$ {self.price:,.2f}"

@dataclass
class Hotel:
    city: str
    name: str
    price_per_night: float
    rating: float

@dataclass
class CarRental:
    city: str
    company: str
    price_per_day: float
    model: str

@dataclass
class TravelRequest:
    origin_cities: List[str]
    destination_cities: List[str]
    mandatory_cities: List[str]
    pax_adults: int
    pax_children: int
    start_date: datetime
    weight_cost: float # 0.0 to 1.0 (1.0 = Minimize Cost only)
    weight_time: float # 0.0 to 1.0 (1.0 = Minimize Time only)
    allow_open_jaw: bool = True
