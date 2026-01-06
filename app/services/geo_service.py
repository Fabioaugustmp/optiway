import math
from typing import Optional, Tuple, List, Dict
from datetime import datetime, timedelta
from app.schemas.travel import Flight

# Simple internal DB of airport coordinates (Latitude, Longitude)
AIRPORT_COORDS = {
    "GRU": (-23.4356, -46.4731), # Sao Paulo
    "GIG": (-22.8089, -43.2436), # Rio
    "CNF": (-19.6244, -43.9719), # Belo Horizonte
    "BSB": (-15.869, -47.9208),  # Brasilia
    "SSA": (-12.9086, -38.3225), # Salvador
    "MIA": (25.7959, -80.2870),  # Miami
    "MCO": (28.4312, -81.3080),  # Orlando
    "JFK": (40.6413, -73.7781),  # New York
    "LHR": (51.4700, -0.4543),   # London
    "CDG": (49.0097, 2.5479),    # Paris
    # Add more as needed or use an external library
}

CITY_TO_IATA = {
    "São Paulo": "GRU",
    "Rio de Janeiro": "GIG",
    "Belo Horizonte": "CNF",
    "Brasília": "BSB",
    "Miami": "MIA",
    "Orlando": "MCO",
    "New York": "JFK",
    "London": "LHR",
    "Paris": "CDG"
}

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
    iata = CITY_TO_IATA.get(city)
    if iata:
        return AIRPORT_COORDS.get(iata)
    return None

def find_nearest_airport(target_city: str) -> Optional[Tuple[str, float]]:
    """
    Returns (Nearest City Name, Distance in KM)
    """
    target_coords = get_coords(target_city)
    if not target_coords:
        return None

    nearest_city = None
    min_dist = float('inf')

    for city, iata in CITY_TO_IATA.items():
        if city == target_city: continue

        coords = AIRPORT_COORDS.get(iata)
        if coords:
            dist = haversine_distance(target_coords, coords)
            if dist < min_dist:
                min_dist = dist
                nearest_city = city

    return nearest_city, min_dist

def suggest_ground_transport(origin_city: str, dest_city: str, distance_km: float) -> str:
    if distance_km < 400:
        hours = distance_km / 80.0
        return f"Car Rental suggested. Drive approx {hours:.1f} hours ({distance_km:.1f} km)."
    else:
        return "Distance too far for driving recommendation. Check trains or buses."

def generate_ground_segments(cities: List[str], start_date: datetime) -> List[Flight]:
    """
    Generates synthetic 'Flight' objects representing ground transport between nearby cities.
    """
    ground_segments = []

    for i in range(len(cities)):
        for j in range(len(cities)):
            if i == j: continue

            city_a = cities[i]
            city_b = cities[j]

            coords_a = get_coords(city_a)
            coords_b = get_coords(city_b)

            if coords_a and coords_b:
                dist = haversine_distance(coords_a, coords_b)

                # Check if feasibly drivable (e.g., < 500km)
                if dist < 500:
                    # Estimate logic
                    # Speed: 80km/h
                    # Price: Rent R$ 150/day + Gas R$ 0.8/km?
                    # Let's approx R$ 2.00 per km (inc rental share + gas)

                    duration_hours = dist / 80.0
                    duration_minutes = int(duration_hours * 60)
                    price = dist * 2.0

                    # Create Segment
                    # We set airline to "Ground Transport" so UI can distinguish
                    seg = Flight(
                        origin=city_a,
                        destination=city_b,
                        price=round(price, 2),
                        duration_minutes=duration_minutes,
                        airline="🚗 Carro/Ônibus",
                        departure_time=start_date + timedelta(hours=8), # Mock dep
                        arrival_time=start_date + timedelta(hours=8, minutes=duration_minutes),
                        stops=0,
                        baggage="Unlimited",
                        details=f"Distância: {dist:.1f}km"
                    )
                    ground_segments.append(seg)

    return ground_segments
