import math
from typing import Optional, Tuple, List, Dict
from datetime import datetime, timedelta
from app.schemas.travel import Flight, CarRental
from app.services.location_service import get_location_service

# The hardcoded tables are now managed centrally by LocationService

def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    R = 6371  # Radius of earth in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = R * c
    return d

def get_coords(city: str) -> Optional[Tuple[float, float]]:
    service = get_location_service()
    # If input is already an IATA
    if len(city) == 3 and city.isalpha():
        return service.get_coords(city)
    
    # Otherwise resolve IATA first
    iata = service.resolve_iata(city)
    return service.get_coords(iata)

def find_nearest_airport(target_city: str) -> Optional[Tuple[str, float]]:
    """
    Returns (Nearest City Name, Distance in KM)
    """
    target_coords = get_coords(target_city)
    if not target_coords:
        return None

    service = get_location_service()
    nearest_city = None
    min_dist = float('inf')

    # Iterate through all known airports in the service
    for info in service.search_index:
        if info.city == target_city or info.iata == target_city: 
            continue

        coords = (info.lat, info.lon)
        dist = haversine_distance(target_coords, coords)
        if dist < min_dist:
            min_dist = dist
            nearest_city = info.city

    return nearest_city, min_dist

def suggest_ground_transport(origin_city: str, dest_city: str, distance_km: float) -> str:
    if distance_km < 400:
        hours = distance_km / 80.0
        return f"Car Rental suggested. Drive approx {hours:.1f} hours ({distance_km:.1f} km)."
    else:
        return "Distance too far for driving recommendation. Check trains or buses."

def generate_ground_segments(
    cities: List[str],
    start_date: datetime,
    cars: List[CarRental] = None
) -> List[Flight]:
    """
    Generates synthetic 'Flight' objects representing ground transport between nearby cities.
    Uses real car rental data if available to estimate pricing.
    """
    ground_segments = []

    # Pre-process cars to map city -> cheapest daily rate
    city_rental_rates = {}
    if cars:
        for car in cars:
            if car.city not in city_rental_rates:
                city_rental_rates[car.city] = car.price_per_day
            else:
                city_rental_rates[car.city] = min(city_rental_rates[car.city], car.price_per_day)

    # Default fallback rate (R$)
    DEFAULT_DAILY_RATE = 150.0
    GAS_PRICE_PER_KM = 0.8
    AVG_SPEED_KMH = 80.0

    for i in range(len(cities)):
        for j in range(len(cities)):
            if i == j: continue

            city_a = cities[i]
            city_b = cities[j]

            coords_a = get_coords(city_a)
            coords_b = get_coords(city_b)

            if coords_a and coords_b:
                dist = haversine_distance(coords_a, coords_b)

                # Check if feasibly drivable (e.g., < 600km)
                if dist < 600:
                    duration_hours = dist / AVG_SPEED_KMH
                    duration_minutes = int(duration_hours * 60)
                    days_needed = max(1, duration_hours / 12.0) # Assume max 12h driving per day? Or just rental days.

                    # Determine Daily Rate
                    rate = city_rental_rates.get(city_a, DEFAULT_DAILY_RATE)

                    # Total Price = (Rate * Days) + (Gas * Distance)
                    # Note: This is total price for the CAR.
                    # The solver usually expects Price PER PERSON if pax > 1.
                    # However, a car fits ~4 people.
                    # To normalize for the solver which multiplies by pax, we might divide by 2 or 3?
                    # Or we just set the price and let the solver treat it as per-person if we want consistent units.
                    # For simplicity, let's assume the price is "per trip" but we divide by 1 (conservative) or 2?
                    # Let's keep it simple: Price displayed is total car cost.
                    # If the solver multiplies by pax, it might penalize cars too much.
                    # BUT `Flight` object implies per-ticket price.
                    # Let's divide by an assumed occupancy of 2 for per-person equivalent?
                    # Or just list the full car price and airline="Car Rental (Total)"

                    total_car_cost = (rate * days_needed) + (GAS_PRICE_PER_KM * dist)

                    # Assume effective per-person price for 2 people to be competitive
                    price_per_person = total_car_cost / 2.0

                    details_str = f"Distância: {dist:.1f}km. Carro: {city_a} -> {city_b}"
                    if city_a in city_rental_rates:
                         details_str += " (Tarifa real encontrada)"

                    # Create Segment
                    seg = Flight(
                        origin=city_a,
                        destination=city_b,
                        price=round(price_per_person, 2),
                        duration_minutes=duration_minutes,
                        airline="🚗 Aluguel de Carro",
                        departure_time=start_date + timedelta(hours=8),
                        arrival_time=start_date + timedelta(hours=8, minutes=duration_minutes),
                        stops=0,
                        baggage="Mala Grande",
                        details=details_str
                    )
                    ground_segments.append(seg)

    return ground_segments
