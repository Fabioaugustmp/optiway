import requests
from typing import List, Dict
from app.schemas.travel import Flight, Hotel, CarRental, TravelRequest, SolverResult
from app.services.geo_service import get_coords


SOLVER_SERVICE_URL = "http://localhost:8002/api/v1/solve"


def solve_itinerary(
    request: TravelRequest,
    flights: List[Flight],
    hotels: List[Hotel],
    cars: List[CarRental]
) -> SolverResult:
    """Call the external solver microservice and return its result."""
    try:
        # Serialize datetimes and Pydantic models to JSON-friendly types
        try:
            from fastapi.encoders import jsonable_encoder
            payload = jsonable_encoder({
                "travel_request": request,
                "flights": flights,
                "hotels": hotels,
                "cars": cars
            })
        except Exception:
            # Fallback: convert using dict() and str for datetimes
            payload = {
                "travel_request": request.dict(),
                "flights": [f.dict() for f in flights],
                "hotels": [h.dict() for h in hotels],
                "cars": [c.dict() for c in cars]
            }

        resp = requests.post(SOLVER_SERVICE_URL, json=payload, timeout=30)
        resp.raise_for_status()

        data = resp.json()

        # Convert response to SolverResult
        # Pydantic models accept dicts so we can reuse SolverResult
        result = SolverResult(**data)
        return result

    except Exception as e:
        return SolverResult(
            status=f"Error: {e}",
            itinerary=[],
            total_cost=0.0,
            total_duration=0,
            warning_message=str(e),
            hotels_found=hotels
        )
