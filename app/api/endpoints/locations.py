from fastapi import APIRouter, Query, Depends
from typing import List
from app.services.location_service import get_location_service, LocationService

router = APIRouter(prefix="/locations", tags=["locations"])

@router.get("/search")
async def search_locations(
    q: str = Query(..., min_length=1, description="Search term (city, name or IATA)"),
    service: LocationService = Depends(get_location_service)
):
    """
    Search for airports/locations for autocomplete.
    Returns a list of matching airports including IATA, city and name.
    """
    results = service.search(q)
    return [
        {
            "iata": a.iata,
            "name": a.name,
            "city": a.city,
            "country": a.country,
            "display": f"{a.city} ({a.iata}) - {a.name}"
        }
        for a in results
    ]
