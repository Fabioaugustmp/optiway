from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class FlightSchema(BaseModel):
    origin: str
    destination: str
    price: float
    duration_minutes: int
    airline: str
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    stops: int = 0
    baggage: str = "N/A"
    flight_number: str = "N/A"
    details: str = ""

class HotelSchema(BaseModel):
    city: str
    name: str
    price_per_night: float
    rating: float

class CarRentalSchema(BaseModel):
    city: str
    company: str
    price_per_day: float
    model: str

class TravelRequestSchema(BaseModel):
    origin_cities: List[str]
    destination_cities: List[str]
    mandatory_cities: List[str]
    pax_adults: int
    pax_children: int
    start_date: datetime
    return_date: Optional[datetime] = None
    is_round_trip: bool = False
    weight_cost: float
    weight_time: float
    stay_days_per_city: int = 1
    daily_cost_per_person: float = 0.0

class ItineraryLegSchema(BaseModel):
    origin: str
    destination: str
    flight: Optional[FlightSchema] = None
    price: float
    duration: int
    price_formatted: str

class SolveResponseSchema(BaseModel):
    status: str
    itinerary: List[ItineraryLegSchema]
    total_cost: float
    total_duration: int
    warning_message: Optional[str] = None
    cost_breakdown: Optional[Dict[str, float]] = None

class SolveRequestSchema(BaseModel):
    travel_request: TravelRequestSchema
    flights: List[FlightSchema]
    hotels: List[HotelSchema]
    cars: List[CarRentalSchema]
