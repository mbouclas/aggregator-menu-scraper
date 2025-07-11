"""
Scraper implementations for different websites.
"""

from .base_scraper import BaseScraper
from .example_scraper import ExampleScraper
from .foody_scraper import FoodyScraper

__all__ = [
    'BaseScraper',
    'ExampleScraper',
    'FoodyScraper'
]
