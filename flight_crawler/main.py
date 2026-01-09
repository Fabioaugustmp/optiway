from fastapi import FastAPI, HTTPException
from flight_crawler.core.models import FlightSearchInput, CarSearchInput
from flight_crawler.services.crawler_service import CrawlerService
from typing import List, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Flight Crawler API", version="1.0.0")

@app.post("/api/v1/crawl")
async def crawl_flights(inputs: List[FlightSearchInput]):
    service = CrawlerService()
    try:
        results = await service.crawl(inputs)
        return {"status": "success", "data": results}
    except Exception as e:
        logging.error(f"Crawl failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/crawl-cars")
async def crawl_cars(inputs: List[CarSearchInput]):
    """
    Endpoint to trigger car rental crawling.
    """
    service = CrawlerService()
    try:
        results = await service.crawl_cars(inputs)
        return {"status": "success", "data": results}
    except Exception as e:
        logging.error(f"Car Crawl failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
