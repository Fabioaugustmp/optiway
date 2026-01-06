from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import User, SearchHistory, Itinerary, FlightOption
from app.core.security import get_current_user
from app.schemas.travel import Flight, TravelRequest, SolverResult
from app.services.crawler_service import get_crawler
from app.services.solver_service import solve_itinerary
from app.services.geo_service import find_nearest_airport, suggest_ground_transport, generate_ground_segments
from app.core.config import settings
import json

router = APIRouter()

@router.post("/solve", response_model=SolverResult)
def solve_trip(
    request: TravelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Init Crawler
    provider = "Amadeus API"
    if request.use_mock_data or not settings.AMADEUS_API_KEY:
        provider = "Mock Data"

    crawler = get_crawler(
        provider=provider,
        key=settings.AMADEUS_API_KEY,
        secret=settings.AMADEUS_API_SECRET
    )

    all_cities = list(set(request.origin_cities + request.destination_cities + request.mandatory_cities))
    
    # Expand graph with nearby airports for cities
    expanded_set = set(all_cities)
    for city in all_cities:
        nearest = find_nearest_airport(city)
        if nearest:
            near_city, dist = nearest
            # Add nearest hub if within 400km (e.g. Ituiutaba -> Uberlandia is ~130km)
            if dist < 400 and near_city != city:
                expanded_set.add(near_city)
    
    all_cities = list(expanded_set)
    flights = []

    # 2. Fetch Flights
    for orig in all_cities:
        dests = [c for c in all_cities if c != orig]
        if dests:
            flights.extend(crawler.fetch_flights(orig, dests, request.start_date, request.pax_adults, request.pax_children))

    # 3. Fetch Car Rentals (Moved up to support ground segment generation)
    cars = crawler.fetch_car_rentals(all_cities)

    # 4. Inject Ground Segments using Real Car Data
    ground_legs = generate_ground_segments(all_cities, request.start_date, cars=cars)
    flights.extend(ground_legs)

    # 5. Fetch Hotels
    hotels = crawler.fetch_hotels(all_cities)

    # 6. Solve
    result = solve_itinerary(request, flights, hotels, cars)

    # 7. Handle Failures / Nearest Airport Logic
    suggestion_msg = None
    if result.status != "Optimal":
        # Attempt to suggest alternatives for destinations
        suggestions = []
        for dest in request.destination_cities:
            inbound = [f for f in flights if f.destination == dest]
            if not inbound:
                nearest = find_nearest_airport(dest)
                if nearest:
                    near_city, dist = nearest
                    ground_transport = suggest_ground_transport(near_city, dest, dist)
                    suggestions.append(f"Fly to {near_city} and take ground transport ({ground_transport})")

        if suggestions:
            suggestion_msg = " | ".join(suggestions)
            result.warning_message = suggestion_msg

    # 8. Save History
    try:
        search_rec = SearchHistory(
            user_id=current_user.id,
            origin=",".join(request.origin_cities),
            destinations=",".join(request.destination_cities),
            start_date=request.start_date
        )
        db.add(search_rec)
        db.commit()
        db.refresh(search_rec)

        # Save All Fetched Flights (Cache)
        saved_flight_keys = set()
        for f in flights:
            if isinstance(f, str): continue
            if hasattr(f, 'origin'):
                f_key = f"{f.origin}-{f.destination}-{f.airline}-{f.price}"
                if f_key in saved_flight_keys:
                    continue
                saved_flight_keys.add(f_key)

                fo = FlightOption(
                    search_id=search_rec.id,
                    origin=f.origin,
                    destination=f.destination,
                    airline=f.airline,
                    price=f.price,
                    duration=f.duration_minutes,
                    stops=f.stops,
                    flight_number=f.flight_number,
                    departure_time=f.departure_time,
                    arrival_time=f.arrival_time
                )
                db.add(fo)
        db.commit()

        # Save Itinerary
        if result.status == "Optimal":
            itinerary_rec = Itinerary(
                search_id=search_rec.id,
                total_cost=result.total_cost,
                total_duration=result.total_duration,
                details_json=json.dumps([leg.dict() for leg in result.itinerary], default=str)
            )
            db.add(itinerary_rec)
            db.commit()
    except Exception as e:
        print(f"DB Save Error: {e}")
        # Continue execution to return result

    # Prepare Alternatives Grouped by Leg
    alternatives_map = {}
    for f in flights:
        if hasattr(f, 'origin'):
            key = f"{f.origin}-{f.destination}"
            if key not in alternatives_map:
                alternatives_map[key] = []
            alternatives_map[key].append(f)
    
    result.alternatives = alternatives_map

    return result
