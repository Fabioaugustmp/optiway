import pytest
from flight_crawler.core.models import FlightSearchInput, FlightResult
from flight_crawler.services.crawler_service import CrawlerService
from flight_crawler.scrapers.google_flights import GoogleFlightsScraper

def test_models():
    input_data = FlightSearchInput(
        origin="JFK",
        destination="LHR",
        departure_date="2024-12-25"
    )
    assert input_data.origin == "JFK"
    assert input_data.passengers == 1

def test_crawler_service_init():
    service = CrawlerService()
    assert "google_flights" in service.scrapers
    assert isinstance(service.scrapers["google_flights"], GoogleFlightsScraper)

@pytest.mark.asyncio
async def test_crawler_service_scrape_mock():
    # This test verifies the service logic without needing a browser
    service = CrawlerService()

    # Mock the browser manager start/stop
    async def mock_start(): pass
    async def mock_stop(): pass
    service.browser_manager.start = mock_start
    service.browser_manager.stop = mock_stop

    # Mock the scraper's scrape method
    async def mock_scrape(search_input):
        return [
            FlightResult(
                airline="Test",
                flight_number="123",
                departure_time="2024-01-01T10:00:00",
                arrival_time="2024-01-01T14:00:00",
                price=100.0,
                deep_link="http://test.com",
                source_scraper="test"
            )
        ]

    service.scrapers["google_flights"].scrape = mock_scrape

    inputs = [FlightSearchInput(origin="A", destination="B", departure_date="2024-01-01")]
    results = await service.crawl(inputs)

    assert "google_flights" in results
    assert len(results["google_flights"]) == 1
    assert results["google_flights"][0].airline == "Test"
