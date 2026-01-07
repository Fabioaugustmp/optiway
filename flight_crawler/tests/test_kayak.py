import pytest
from flight_crawler.services.crawler_service import CrawlerService
from flight_crawler.scrapers.kayak import KayakScraper

def test_crawler_service_kayak():
    service = CrawlerService()
    assert "kayak" in service.scrapers
    assert isinstance(service.scrapers["kayak"], KayakScraper)
