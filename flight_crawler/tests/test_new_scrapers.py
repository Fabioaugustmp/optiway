import pytest
from flight_crawler.services.crawler_service import CrawlerService
from flight_crawler.scrapers.latam import LatamScraper
from flight_crawler.scrapers.azul import AzulScraper
from flight_crawler.scrapers.gol import GolScraper

def test_crawler_service_new_scrapers():
    service = CrawlerService()
    assert "latam" in service.scrapers
    assert "azul" in service.scrapers
    assert "gol" in service.scrapers

    assert isinstance(service.scrapers["latam"], LatamScraper)
    assert isinstance(service.scrapers["azul"], AzulScraper)
    assert isinstance(service.scrapers["gol"], GolScraper)
