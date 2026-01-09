"""
Solver Service - Main Application
"""

from fastapi import FastAPI
from solver_service.api.endpoints import router as solver_router

app = FastAPI(
    title="OptiWay Solver Service",
    version="1.0.0",
    description="Multi-city travel itinerary optimization API"
)

# Include routers
app.include_router(solver_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "OptiWay Solver Service",
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "solver_service.main:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )
