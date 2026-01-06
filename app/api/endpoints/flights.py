from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import User, SearchHistory, Itinerary, FlightOption
from app.core.security import get_current_user
from app.schemas.travel import Flight, TravelRequest, SolverResult, Hotel
from app.db.models import User, SearchHistory, Itinerary, FlightOption, HotelOption
from app.services.crawler_service import get_crawler
from app.services.solver_service import solve_itinerary
from app.services.geo_service import find_nearest_airport, suggest_ground_transport, generate_ground_segments
from app.core.config import settings
import json
from datetime import datetime, timedelta

router = APIRouter()

def get_cached_hotels(db: Session, cities: List[str]) -> List[Hotel]:
    # Cache window: 24 hours
    cache_cutoff = datetime.utcnow() - timedelta(hours=24)
    cached_hotels = []
    
    for city in cities:
        results = db.query(HotelOption).join(SearchHistory).filter(
            HotelOption.city == city,
            SearchHistory.created_at >= cache_cutoff
        ).all()
        
        for h in results:
            cached_hotels.append(Hotel(
                city=h.city,
                name=h.name,
                price_per_night=h.price,
                rating=h.rating
            ))
    return cached_hotels

def get_cached_flights(db: Session, origin: str, destinations: List[str], start_date: datetime) -> List[Flight]:
    # Cache window: 24 hours
    cache_cutoff = datetime.utcnow() - timedelta(hours=24)
    cached_flights = []
    
    # Match Date strictly by Day (ignore time)
    start_of_day = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    for dest in destinations:
        results = db.query(FlightOption).join(SearchHistory).filter(
            FlightOption.origin == origin,
            FlightOption.destination == dest,
            SearchHistory.created_at >= cache_cutoff,
            SearchHistory.start_date >= start_of_day,
            SearchHistory.start_date <= end_of_day
        ).all()
        
        for fo in results:
             cached_flights.append(Flight(
                 origin=fo.origin,
                 destination=fo.destination,
                 price=fo.price,
                 duration_minutes=fo.duration,
                 airline=fo.airline,
                 departure_time=fo.departure_time,
                 arrival_time=fo.arrival_time,
                 stops=fo.stops,
                 flight_number=fo.flight_number,
                 baggage="N/A",
                 details=f"{fo.origin}->{fo.destination} ({fo.flight_number})"
             ))
             
    return cached_flights

# ... existing get_cached_flights ...

@router.post("/solve", response_model=SolverResult)
def solve_trip(
    request: TravelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ... (init crawler, graph expansion) ...
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
            if dist < 400 and near_city != city:
                expanded_set.add(near_city)
    
    all_cities = list(expanded_set)
    flights = []
    
    cached_flights_set = set() # Track cached items

    # 2. Fetch Flights (with Cache)
    # ... (existing flight cache logic) ...
    for orig in all_cities:
        dests = [c for c in all_cities if c != orig]
        if dests:
            # Check Cache First
            cached = get_cached_flights(db, orig, dests, request.start_date)
            if cached:
                print(f"Flight Cache Hit for {orig} -> {dests}")
                flights.extend(cached)
                for f in cached:
                    f_key = f"{f.origin}-{f.destination}-{f.airline}-{f.price}-{f.flight_number}"
                    cached_flights_set.add(f_key)

            found_dests = set(f.destination for f in cached)
            missing_dests = [d for d in dests if d not in found_dests]
            
            if missing_dests:
                print(f"Fetching API for missing flights: {orig} -> {missing_dests}")
                new_flights = crawler.fetch_flights(orig, missing_dests, request.start_date, request.pax_adults, request.pax_children)
                flights.extend(new_flights)

    # 3. Fetch Car Rentals
    cars = crawler.fetch_car_rentals(all_cities)

    # 4. Inject Ground Segments
    ground_legs = generate_ground_segments(all_cities, request.start_date, cars=cars)
    flights.extend(ground_legs)

    # 5. Fetch Hotels (with Cache)
    hotels = []
    cached_hotels_set = set()
    if request.search_hotels:
        # Check Cache
        cached_h = get_cached_hotels(db, all_cities)
        
        # Determine missing cities
        found_cities = set(h.city for h in cached_h)
        missing_cities = [c for c in all_cities if c not in found_cities]
        
        if cached_h:
            print(f"Hotel Cache Hit for {len(found_cities)} cities.")
            hotels.extend(cached_h)
            for h in cached_h:
                cached_hotels_set.add(f"{h.city}-{h.name}")
        
        # Fetch Missing
        if missing_cities:
            print(f"Fetching API for missing hotels in: {missing_cities}")
            new_hotels = crawler.fetch_hotels(missing_cities)
            hotels.extend(new_hotels)


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
        # ONLY IF NOT FROM CACHE
        saved_flight_keys = set()
        new_records = 0
        for f in flights:
            if isinstance(f, str): continue
            if hasattr(f, 'origin'):
                f_key_id = f"{f.origin}-{f.destination}-{f.airline}-{f.price}-{f.flight_number}"
                
                # Deduplicate within this insert
                if f_key_id in saved_flight_keys:
                    continue
                saved_flight_keys.add(f_key_id)
                
                # CHECK IF FROM CACHE
                if f_key_id in cached_flights_set:
                     continue # Skip db write for cached items

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
                new_records += 1
        
        if new_records > 0:
            db.commit()
            print(f"Saved {new_records} new flight options to DB.")
        else:
            print("No new flights to save (all cached).")
            
        # Save Fetched Hotels (Cache)
        new_hotels_count = 0
        saved_hotel_keys = set()
        for h in hotels:
            # Check if from cache
            h_key = f"{h.city}-{h.name}"
            
            if h_key in cached_hotels_set:
                continue # Skip existing in this run (from cache)
            
            if h_key in saved_hotel_keys:
                continue # Skip duplicates in current list
            
            saved_hotel_keys.add(h_key)
            
            ho = HotelOption(
                search_id=search_rec.id,
                city=h.city,
                name=h.name,
                price=h.price_per_night,
                rating=h.rating
            )
            db.add(ho)
            new_hotels_count += 1
            
        if new_hotels_count > 0:
            db.commit()
            print(f"Saved {new_hotels_count} new hotel options to DB.")


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
