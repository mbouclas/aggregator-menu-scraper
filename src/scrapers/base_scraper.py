"""
Base scraper class for web scraping with unified JSON output format.
Uses Playwright for browser automation.
"""
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse
from playwright.sync_api import Page, ElementHandle

from ..common.config import ScraperConfig
from ..common.logging_config import get_logger
from ..common.playwright_utils import (
    PlaywrightManager,
    wait_for_element,
    safe_find_element,
    safe_find_elements,
    get_text_content,
    get_attribute,
    wait_for_page_load,
    scroll_to_bottom,
    scroll_to_element
)


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    
    Provides a unified interface and JSON output format for scraping
    different websites while handling configuration, logging, and error handling.
    """
    
    def __init__(self, config: ScraperConfig, target_url: str):
        """
        Initialize the scraper with configuration and target URL.
        
        Args:
            config: ScraperConfig instance with website-specific settings
            target_url: The URL to scrape
        """
        self.config = config
        self.target_url = target_url
        self.logger = get_logger(f"scraper.{config.domain}")
        
        # Timestamps
        self.scraped_at: Optional[datetime] = None
        self.processed_at: Optional[datetime] = None
        
        # Data storage
        self._restaurant_info: Dict[str, Any] = {}
        self._categories: List[Dict[str, Any]] = []
        self._products: List[Dict[str, Any]] = []
        self._metadata: Dict[str, Any] = {}
        self._errors: List[Dict[str, Any]] = []
        
        # Playwright components
        self.playwright_manager: Optional[PlaywrightManager] = None
        self.page: Optional[Page] = None
        
        self.logger.info(f"Initialized scraper for {config.domain} with URL: {target_url}")
    
    def scrape(self) -> Dict[str, Any]:
        """
        Main scraping method that orchestrates the entire process.
        
        Returns:
            Complete scraped data in unified JSON format
        """
        self.logger.info(f"Starting scrape of {self.target_url}")
        self.scraped_at = datetime.now(timezone.utc)
        
        try:
            # Initialize Playwright if needed
            if self.config.requires_javascript:
                self._setup_browser()
                self._navigate_to_page()
            
            # Extract data using abstract methods
            self._restaurant_info = self.extract_restaurant_info()
            self._categories = self.extract_categories()
            self._products = self.extract_products()
            
            # Set processing timestamp
            self.processed_at = datetime.now(timezone.utc)
            
            # Generate metadata
            self._metadata = self._generate_metadata()
            
            # Build final output
            output = self._build_output()
            
            self.logger.info(f"Successfully scraped {len(self._products)} products from {len(self._categories)} categories")
            return output
            
        except Exception as e:
            self.logger.error(f"Scraping failed: {str(e)}", exc_info=True)
            self._add_error("scraping_failed", str(e))
            
            # Return partial data with error information
            self.processed_at = datetime.now(timezone.utc)
            self._metadata = self._generate_metadata()
            return self._build_output()
        finally:
            # Clean up browser resources
            self._cleanup_browser()
    
    @abstractmethod
    def extract_restaurant_info(self) -> Dict[str, Any]:
        """
        Extract restaurant/establishment information.
        
        Returns:
            Dictionary containing restaurant information:
            {
                "name": str,
                "brand": str,
                "address": str,
                "phone": str,
                "rating": float,
                "delivery_fee": float,
                "minimum_order": float,
                "delivery_time": str,
                "cuisine_types": List[str]
            }
        """
        pass
    
    @abstractmethod
    def extract_categories(self) -> List[Dict[str, Any]]:
        """
        Extract product categories.
        
        Returns:
            List of category dictionaries:
            [
                {
                    "id": str,
                    "name": str,
                    "description": str,
                    "product_count": int
                }
            ]
        """
        pass
    
    @abstractmethod
    def extract_products(self) -> List[Dict[str, Any]]:
        """
        Extract product information.
        
        Returns:
            List of product dictionaries:
            [
                {
                    "id": str,
                    "name": str,
                    "description": str,
                    "price": float,
                    "original_price": float,
                    "currency": str,
                    "discount_percentage": float,
                    "category": str,
                    "image_url": str,
                    "availability": bool,
                    "options": List[Dict[str, Any]]
                }
            ]
        """
        pass
    
    def _generate_metadata(self) -> Dict[str, Any]:
        """
        Generate metadata for the scraping session.
        
        Returns:
            Metadata dictionary
        """
        return {
            "scraper_version": "1.0.0",
            "domain": self.config.domain,
            "scraping_method": self.config.scraping_method,
            "requires_javascript": self.config.requires_javascript,
            "anti_bot_protection": self.config.anti_bot_protection,
            "url_pattern": self.config.url_pattern,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "processing_duration_seconds": self._calculate_processing_duration(),
            "error_count": len(self._errors),
            "product_count": len(self._products),
            "category_count": len(self._categories)
        }
    
    def _calculate_processing_duration(self) -> Optional[float]:
        """Calculate processing duration in seconds."""
        if self.scraped_at and self.processed_at:
            return (self.processed_at - self.scraped_at).total_seconds()
        return None
    
    def _build_output(self) -> Dict[str, Any]:
        """
        Build the final unified JSON output structure.
        
        Returns:
            Complete output dictionary in unified format
        """
        return {
            "metadata": self._metadata,
            "source": {
                "url": self.target_url,
                "domain": self.config.domain,
                "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None
            },
            "restaurant": self._restaurant_info,
            "categories": self._categories,
            "products": self._products,
            "summary": {
                "total_products": len(self._products),
                "total_categories": len(self._categories),
                "price_range": self._calculate_price_range(),
                "available_products": len([p for p in self._products if p.get("availability", True)]),
                "products_with_discounts": len([p for p in self._products if p.get("discount_percentage", 0) > 0])
            },
            "errors": self._errors
        }
    
    def _calculate_price_range(self) -> Dict[str, Any]:
        """Calculate price range from extracted products."""
        prices = [p.get("price", 0) for p in self._products if p.get("price") is not None]
        
        if not prices:
            return {"min": None, "max": None, "average": None, "currency": "EUR"}
        
        return {
            "min": min(prices),
            "max": max(prices),
            "average": round(sum(prices) / len(prices), 2),
            "currency": self._products[0].get("currency", "EUR") if self._products else "EUR"
        }
    
    def _add_error(self, error_type: str, message: str, context: Dict[str, Any] = None) -> None:
        """
        Add an error to the error log.
        
        Args:
            error_type: Type of error (e.g., 'extraction_failed', 'parsing_error')
            message: Error message
            context: Additional context information
        """
        error = {
            "type": error_type,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": context or {}
        }
        self._errors.append(error)
        self.logger.warning(f"Error recorded: {error_type} - {message}")
    
    def save_output(self, output_dir: str = "output", filename: str = None) -> str:
        """
        Save the scraped data to a JSON file.
        
        Args:
            output_dir: Directory to save the output file
            filename: Custom filename (if None, generates based on domain and timestamp)
            
        Returns:
            Path to the saved file
        """
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename if not provided
        if filename is None:
            # Try to use restaurant name from scraped data
            output_data = self.scrape() if not hasattr(self, '_output_data') else self._output_data
            
            # Extract scraper name from domain
            scraper_name = self.config.domain.split('.')[0]  # e.g., 'foody' from 'foody.com.cy'
            
            # Try to get restaurant name
            restaurant_name = "unknown"
            if output_data and 'restaurant' in output_data and 'name' in output_data['restaurant']:
                raw_name = output_data['restaurant']['name']
                if raw_name:
                    # Sanitize restaurant name for filename
                    import re
                    clean_name = raw_name.lower()
                    clean_name = re.sub(r'\s+(online\s+delivery|order\s+from\s+foody|delivery)\s*$', '', clean_name)
                    clean_name = re.sub(r'[^\w\s-]', '', clean_name)  # Remove special chars
                    clean_name = re.sub(r'\s+', '-', clean_name)  # Replace spaces with hyphens
                    clean_name = re.sub(r'-+', '-', clean_name)  # Collapse multiple hyphens
                    clean_name = clean_name.strip('-')  # Remove leading/trailing hyphens
                    
                    if clean_name:
                        restaurant_name = clean_name
            
            # Generate filename: scraper_restaurant.json
            filename = f"{scraper_name}_{restaurant_name}.json"
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        file_path = os.path.join(output_dir, filename)
        
        # Get the scraped data
        output_data = self.scrape() if not hasattr(self, '_output_data') else self._output_data
        
        # Save to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Output saved to: {file_path}")
        return file_path
    
    def get_config(self) -> ScraperConfig:
        """Get the scraper configuration."""
        return self.config
    
    def get_target_url(self) -> str:
        """Get the target URL."""
        return self.target_url
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Get list of errors encountered during scraping."""
        return self._errors.copy()
    
    def has_errors(self) -> bool:
        """Check if any errors were encountered."""
        return len(self._errors) > 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the scraping results."""
        return {
            "domain": self.config.domain,
            "url": self.target_url,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "products_found": len(self._products),
            "categories_found": len(self._categories),
            "errors_encountered": len(self._errors),
            "success": len(self._errors) == 0
        }
    
    def _setup_browser(self) -> None:
        """Set up Playwright browser and page."""
        self.logger.debug("Setting up Playwright browser")
        self.playwright_manager = PlaywrightManager(
            headless=self.config.extra_config.get('headless', True),
            timeout=self.config.extra_config.get('timeout', 30000)
        )
        self.playwright_manager.start()
        
        # Create browser page
        browser_type = self.config.extra_config.get('browser_type', 'chromium')
        self.page = self.playwright_manager.create_driver(browser_type=browser_type)
        
        # Set viewport size if specified
        if 'viewport' in self.config.extra_config:
            self.page.set_viewport_size(self.config.extra_config['viewport'])
        
        self.logger.debug("Browser setup complete")
    
    def _navigate_to_page(self) -> None:
        """Navigate to the target URL."""
        if not self.page:
            raise RuntimeError("Browser not initialized")
        
        max_retries = self.config.extra_config.get('max_retries', 3)
        retry_delay = self.config.extra_config.get('retry_delay', 2)
        
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Navigating to {self.target_url} (attempt {attempt + 1})")
                self.page.goto(self.target_url, wait_until='domcontentloaded')
                
                # Wait for page to fully load
                wait_for_page_load(self.page)
                
                # Additional wait if specified
                if 'page_load_wait' in self.config.extra_config:
                    self.page.wait_for_timeout(self.config.extra_config['page_load_wait'] * 1000)
                
                self.logger.debug("Navigation successful")
                return
                
            except Exception as e:
                self.logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    self.page.wait_for_timeout(retry_delay * 1000)
                else:
                    raise
    
    def _cleanup_browser(self) -> None:
        """Clean up browser resources."""
        if self.page:
            try:
                self.playwright_manager.quit_driver(self.page)
            except Exception as e:
                self.logger.warning(f"Error closing page: {e}")
        
        if self.playwright_manager:
            try:
                self.playwright_manager.close()
            except Exception as e:
                self.logger.warning(f"Error closing Playwright: {e}")
        
        self.page = None
        self.playwright_manager = None
    
    # Helper methods for subclasses to use
    def find_element(self, selector: str) -> Optional[ElementHandle]:
        """Find element on page using CSS selector."""
        if not self.page:
            self.logger.warning("Page not initialized, cannot find element")
            return None
        return safe_find_element(self.page, selector)
    
    def find_elements(self, selector: str) -> List[ElementHandle]:
        """Find multiple elements on page using CSS selector."""
        if not self.page:
            self.logger.warning("Page not initialized, cannot find elements")
            return []
        return safe_find_elements(self.page, selector)
    
    def wait_for_selector(self, selector: str, timeout: int = 10000) -> Optional[ElementHandle]:
        """Wait for element to appear on page."""
        if not self.page:
            self.logger.warning("Page not initialized, cannot wait for selector")
            return None
        try:
            return wait_for_element(self.page, selector, timeout)
        except Exception as e:
            self.logger.warning(f"Failed to find selector {selector}: {e}")
            return None
    
    def get_element_text(self, element: Optional[ElementHandle], default: str = "") -> str:
        """Get text content from element."""
        return get_text_content(element, default)
    
    def get_element_attribute(self, element: Optional[ElementHandle], attribute: str, default: str = "") -> str:
        """Get attribute value from element."""
        return get_attribute(element, attribute, default)
    
    def scroll_page_to_bottom(self) -> None:
        """Scroll page to bottom."""
        if self.page:
            scroll_to_bottom(self.page)
    
    def scroll_to_element_view(self, element: Union[ElementHandle, str]) -> None:
        """Scroll element into view."""
        if self.page:
            scroll_to_element(self.page, element)
