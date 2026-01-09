"""
Scrapers Module - Collection of flight data scrapers
"""

from flight_crawler.scrapers.google_flights import GoogleFlightsScraper
from flight_crawler.scrapers.kayak import KayakScraper
from flight_crawler.scrapers.latam import LatamScraper
from flight_crawler.scrapers.azul import AzulScraper
from flight_crawler.scrapers.gol import GolScraper

__all__ = [
    "GoogleFlightsScraper",
    "KayakScraper",
    "LatamScraper",
    "AzulScraper",
    "GolScraper",
]
