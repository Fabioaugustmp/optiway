from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Shared Pydantic Models

class FlightBase(BaseModel):
    origin: str
    destination: str
    price: float
    duration_minutes: int
    airline: str
    departure_time: datetime
    arrival_time: datetime
    stops: int = 0
    baggage: str = "N/A"
    flight_number: str = "N/A"
    details: str = ""

class FlightCreate(FlightBase):
    pass

class Flight(FlightBase):
    pass

class HotelBase(BaseModel):
    city: str
    name: str
    price_per_night: float
    rating: float

class Hotel(HotelBase):
    pass

class CarRentalBase(BaseModel):
    city: str
    company: str
    price_per_day: float
    model: str

class CarRental(CarRentalBase):
    pass

class TravelRequest(BaseModel):
    origin_cities: List[str]
    destination_cities: List[str]
    mandatory_cities: List[str]
    pax_adults: int
    pax_children: int
    start_date: datetime
    return_date: Optional[datetime] = None
    is_round_trip: bool = False
    # Deprecated: kept for backward compatibility
    use_mock_data: bool = False
    # Data provider: "Mock Data", "Amadeus API", "Google Flights", "Kayak"
    provider: Optional[str] = "Mock Data"
    weight_cost: float
    weight_time: float
    allow_open_jaw: bool = True
    stay_days_per_city: int = 1
    daily_cost_per_person: float = 0.0
    search_hotels: bool = False
    search_cars: bool = False

class ItineraryLeg(BaseModel):
    origin: str
    destination: str
    flight: Optional[Flight]
    price: float
    duration: int
    price_formatted: str
    origin_coords: Optional[List[float]] = None
    dest_coords: Optional[List[float]] = None

class SolverResult(BaseModel):
    status: str
    itinerary: List[ItineraryLeg]
    total_cost: float
    total_duration: int
    warning_message: Optional[str] = None
    alternatives: Optional[dict] = None # Key: "Origin-Destination", Value: List[Flight]
    cost_breakdown: Optional[dict] = None
    hotels_found: Optional[List[Hotel]] = []
