from fastapi import FastAPI, HTTPException
from flight_crawler.core.models import FlightSearchInput, CarSearchInput, HotelSearchInput
from flight_crawler.services.crawler_service import CrawlerService
from typing import List, Dict
import logging
import sys
import asyncio

# Note: We don't modify the event loop policy here since we use ThreadPoolExecutor
# with its own event loop for Playwright operations

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Flight Crawler API", version="1.0.0")

@app.post("/api/v1/crawl")
async def crawl_flights(inputs: List[FlightSearchInput]):
    """
    Endpoint to trigger flight crawling.
    Uses a thread pool to run Playwright in a separate thread with its own event loop.
    """
    import traceback
    import concurrent.futures
    
    def run_in_new_loop():
        """Run the crawler in a new event loop in a separate thread."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            service = CrawlerService()
            return loop.run_until_complete(service.crawl(inputs))
        finally:
            loop.close()
    
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_new_loop)
            results = future.result(timeout=120)
        return {"status": "success", "data": results}
    except Exception as e:
        error_msg = str(e) or repr(e) or "Unknown error occurred"
        logging.error(f"Crawl failed: {error_msg}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/v1/crawl-cars")
async def crawl_cars(inputs: List[CarSearchInput]):
    """
    Endpoint to trigger car rental crawling.
    Uses a thread pool to run Playwright in a separate thread with its own event loop.
    """
    import traceback
    import concurrent.futures
    
    def run_in_new_loop():
        """Run the crawler in a new event loop in a separate thread."""
        import asyncio
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            service = CrawlerService()
            return loop.run_until_complete(service.crawl_cars(inputs))
        finally:
            loop.close()
    
    try:
        # Run the crawler in a thread pool with its own event loop
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_new_loop)
            results = future.result(timeout=120)  # 2 minute timeout
        return {"status": "success", "data": results}
    except Exception as e:
        error_msg = str(e) or repr(e) or "Unknown error occurred"
        logging.error(f"Car Crawl failed: {error_msg}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/v1/crawl-hotels")
async def crawl_hotels(inputs: List[HotelSearchInput]):
    """
    Endpoint to trigger hotel crawling.
    Uses a thread pool to run Playwright in a separate thread with its own event loop.
    """
    import traceback
    import concurrent.futures
    
    def run_in_new_loop():
        """Run the crawler in a new event loop in a separate thread."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            service = CrawlerService()
            return loop.run_until_complete(service.crawl_hotels(inputs))
        finally:
            loop.close()
    
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_new_loop)
            results = future.result(timeout=120)  # 2 minute timeout
        return {"status": "success", "data": results}
    except Exception as e:
        error_msg = str(e) or repr(e) or "Unknown error occurred"
        logging.error(f"Hotel Crawl failed: {error_msg}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
