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

@router.get("/validate")
async def validate_locations(
    q: List[str] = Query(..., description="List of location terms to validate"),
    service: LocationService = Depends(get_location_service)
):
    """
    Validates a list of location strings (IATAs or City names).
    Returns a list of invalid entries.
    """
    invalid = []
    # Deduplicate to avoid redundant checks
    terms = list(set(t.strip() for t in q if t.strip()))
    
    for term in terms:
        resolved = service.resolve_iata(term)
        if resolved.upper() not in service.airports:
            invalid.append(term)
    
    return {"valid": len(invalid) == 0, "invalid": invalid}
