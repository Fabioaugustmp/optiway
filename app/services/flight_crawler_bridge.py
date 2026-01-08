"""
Flight Crawler Bridge - Adapter between flight_crawler and app schemas
Converts between flight_crawler models and app.schemas.travel models
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
from app.schemas.travel import Flight
from flight_crawler.core.models import FlightResult as CrawlerFlightResult
from flight_crawler.services.crawler_service import CrawlerService
from flight_crawler.core.models import FlightSearchInput

logger = logging.getLogger(__name__)


class FlightCrawlerBridge:
    """
    Adapter class that bridges flight_crawler service with app architecture.
    Handles conversion between different data models and manages scraper lifecycle.
    """

    def __init__(self):
        self.crawler_service = CrawlerService()
        self.logger = logging.getLogger(self.__class__.__name__)

    def convert_crawler_flight_to_app_flight(
        self,
        crawler_flight: CrawlerFlightResult,
        origin: str,
        destination: str
    ) -> Flight:
        """
        Convert flight_crawler.FlightResult to app.schemas.travel.Flight
        """
        return Flight(
            airline=crawler_flight.airline,
            origin=origin,
            destination=destination,
            departure_time=crawler_flight.departure_time,
            arrival_time=crawler_flight.arrival_time,
            price=crawler_flight.price,
            duration_minutes=self._calculate_duration_minutes(
                crawler_flight.departure_time,
                crawler_flight.arrival_time
            ),
            stops=0,
            baggage="1 checked bag",
            flight_number=crawler_flight.flight_number,
            details=f"{crawler_flight.airline} - {crawler_flight.flight_number} from {crawler_flight.source_scraper}"
        )

    def _calculate_duration_minutes(self, departure: datetime, arrival: datetime) -> int:
        """Calculate flight duration in minutes"""
        try:
            delta = arrival - departure
            return int(delta.total_seconds() / 60)
        except Exception as e:
            self.logger.warning(f"Could not calculate duration: {e}")
            return 0

    async def crawl_flights_async(
        self,
        origin: str,
        destinations: List[str],
        departure_date: datetime,
        scrapers: Optional[List[str]] = None,
        passengers: int = 1,
        return_date: Optional[datetime] = None
    ) -> List[Flight]:
        """
        Crawl flights asynchronously using specified scrapers
        Returns list of Flight objects in app schema format
        """
        try:
            search_inputs = []

            # Create search input for each destination
            for dest in destinations:
                search_input = FlightSearchInput(
                    origin=origin,
                    destination=dest,
                    departure_date=departure_date.strftime("%Y-%m-%d"),
                    return_date=return_date.strftime("%Y-%m-%d") if return_date else None,
                    passengers=passengers,
                    scrapers=scrapers  # None = use all available
                )
                search_inputs.append(search_input)

            # Execute crawl
            crawler_results: Dict[str, List[CrawlerFlightResult]] = await self.crawler_service.crawl(search_inputs)

            # Convert results to app schema
            app_flights: List[Flight] = []

            for search_input in search_inputs:
                for scraper_name, flights in crawler_results.items():
                    # Filter flights for this route
                    route_flights = [
                        f for f in flights
                        if f.source_scraper == scraper_name
                    ]

                    for crawler_flight in route_flights:
                        try:
                            app_flight = self.convert_crawler_flight_to_app_flight(
                                crawler_flight,
                                search_input.origin,
                                search_input.destination
                            )
                            app_flights.append(app_flight)
                        except Exception as e:
                            self.logger.error(f"Error converting flight: {e}")
                            continue

            self.logger.info(f"Crawled {len(app_flights)} flights successfully")
            return app_flights

        except Exception as e:
            self.logger.error(f"Error during crawl: {e}")
            raise

    def crawl_flights(
        self,
        origin: str,
        destinations: List[str],
        departure_date: datetime,
        scrapers: Optional[List[str]] = None,
        passengers: int = 1,
        return_date: Optional[datetime] = None
    ) -> List[Flight]:
        """
        Synchronous wrapper around async crawl_flights.
        Use when you can't use async/await directly.
        """
        try:
            # Run async function in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.crawl_flights_async(
                    origin,
                    destinations,
                    departure_date,
                    scrapers,
                    passengers,
                    return_date
                )
            )
            return result
        except Exception as e:
            self.logger.error(f"Error in synchronous crawl: {e}")
            return []
        finally:
            loop.close()

    def get_available_scrapers(self) -> List[str]:
        """Return list of available scrapers"""
        return list(self.crawler_service.scrapers.keys())


# Singleton instance
_bridge_instance: Optional[FlightCrawlerBridge] = None


def get_crawler_bridge() -> FlightCrawlerBridge:
    """Get or create singleton instance of FlightCrawlerBridge"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = FlightCrawlerBridge()
    return _bridge_instance
