"""
Web scraper package for extracting data from various websites.
"""

from .common import ScraperConfig, ScraperFactory, setup_logging, get_logger

__version__ = "0.1.0"
__all__ = [
    'ScraperConfig',
    'ScraperFactory', 
    'setup_logging',
    'get_logger'
]
