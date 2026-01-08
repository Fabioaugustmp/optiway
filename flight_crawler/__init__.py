"""
Flight Crawler Package - Modularized scraper service
Provides unified access to multiple flight data sources
"""

from flight_crawler.core.models import FlightSearchInput, FlightResult
from flight_crawler.services.crawler_service import CrawlerService
from flight_crawler.core.browser_manager import BrowserManager

# Scraper imports
from flight_crawler.scrapers.google_flights import GoogleFlightsScraper
from flight_crawler.scrapers.kayak import KayakScraper
from flight_crawler.scrapers.latam import LatamScraper
from flight_crawler.scrapers.azul import AzulScraper
from flight_crawler.scrapers.gol import GolScraper

__all__ = [
    # Core models
    "FlightSearchInput",
    "FlightResult",
    # Main service
    "CrawlerService",
    # Browser manager
    "BrowserManager",
    # Individual scrapers
    "GoogleFlightsScraper",
    "KayakScraper",
    "LatamScraper",
    "AzulScraper",
    "GolScraper",
]

__version__ = "1.0.0"
