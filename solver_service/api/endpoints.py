"""
Solver Service API Endpoints
"""

import logging
from fastapi import APIRouter, HTTPException
from solver_service.models.schemas import SolveRequestSchema, SolveResponseSchema
from solver_service.models.solver import solve_itinerary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["solver"])


@router.post("/solve", response_model=SolveResponseSchema)
async def solve_trip(request: SolveRequestSchema) -> SolveResponseSchema:
    """
    Solve multi-city travel itinerary optimization.
    
    Accepts travel requirements and available flights/hotels/cars,
    returns optimized itinerary balancing cost and time.
    
    Args:
        request: SolveRequestSchema containing:
            - travel_request: User preferences (cities, dates, budget weights)
            - flights: List of available flights
            - hotels: List of available hotels
            - cars: List of available car rentals
    
    Returns:
        SolveResponseSchema with optimized itinerary
    
    Raises:
        HTTPException: If solve fails
    """
    try:
        logger.info(
            f"Solving itinerary for {len(request.travel_request.destination_cities)} destinations, "
            f"{len(request.flights)} flights available"
        )
        
        result = solve_itinerary(
            request.travel_request,
            request.flights,
            request.hotels,
            request.cars
        )
        
        logger.info(f"Solution status: {result.status}, itinerary length: {len(result.itinerary)}")
        return result
        
    except Exception as e:
        logger.error(f"Error solving itinerary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Solver failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "solver-service",
        "version": "1.0.0"
    }


@router.get("/info")
async def service_info():
    """Get service information"""
    return {
        "name": "OptiWay Solver Service",
        "version": "1.0.0",
        "description": "Multi-city travel itinerary optimization using TSP and PuLP",
        "endpoints": {
            "solve": "POST /api/v1/solve",
            "health": "GET /api/v1/health",
            "info": "GET /api/v1/info"
        }
    }
