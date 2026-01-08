"""
Solver Service Schemas - Pydantic models for solver requests and responses
"""

from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


class FlightSchema(BaseModel):
    """Flight information for solver"""
    airline: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    duration_minutes: int
    stops: int = 0
    baggage: str = "N/A"
    flight_number: str = "N/A"
    details: str = ""

    class Config:
        from_attributes = True


class HotelSchema(BaseModel):
    """Hotel information for solver"""
    city: str
    name: str
    price_per_night: float
    rating: float = 0.0

    class Config:
        from_attributes = True


class CarRentalSchema(BaseModel):
    """Car rental information for solver"""
    city: str
    company: str
    price_per_day: float
    model: str

    class Config:
        from_attributes = True


class TravelRequestSchema(BaseModel):
    """Travel requirements and preferences"""
    origin_cities: List[str]
    destination_cities: List[str]
    mandatory_cities: List[str]
    pax_adults: int
    pax_children: int
    start_date: datetime
    return_date: Optional[datetime] = None
    is_round_trip: bool = False
    weight_cost: float  # 0.0 to 1.0
    weight_time: float  # 0.0 to 1.0
    allow_open_jaw: bool = True
    stay_days_per_city: int = 1
    daily_cost_per_person: float = 0.0


class SolveRequestSchema(BaseModel):
    """Complete request to solve itinerary"""
    travel_request: TravelRequestSchema
    flights: List[FlightSchema]
    hotels: List[HotelSchema] = []
    cars: List[CarRentalSchema] = []


class ItineraryLegSchema(BaseModel):
    """Single leg of an itinerary"""
    origin: str
    destination: str
    flight: Optional[FlightSchema] = None
    price: float
    duration: int
    price_formatted: str
    origin_coords: Optional[List[float]] = None
    dest_coords: Optional[List[float]] = None


class SolveResponseSchema(BaseModel):
    """Response from solver"""
    status: str  # "Optimal", "Feasible", "Infeasible"
    itinerary: List[ItineraryLegSchema]
    total_cost: float
    total_duration: int
    warning_message: Optional[str] = None
    alternatives: Optional[Dict[str, List[FlightSchema]]] = None
    cost_breakdown: Optional[Dict[str, float]] = None
    hotels_found: Optional[List[HotelSchema]] = []

    class Config:
        from_attributes = True
