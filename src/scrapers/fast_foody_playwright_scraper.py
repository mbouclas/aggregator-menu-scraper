"""
Fast Foody.com.cy scraper implementation using Playwright for maximum performance.

This scraper uses aggressive Playwright optimizations to reduce scraping time
while maintaining data quality and extraction accuracy.
"""
import time
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional, Tuple
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

from .base_scraper import BaseScraper

# Import fast Playwright utilities for optimized performance
try:
    from ..common.fast_playwright_utils import (
        FastPlaywrightManager, 
        create_fast_driver,
        fast_page_fetch,
        fast_wait_for_element,
        fast_find_elements,
        fast_get_text_content,
        fast_scroll_to_bottom
    )
    FAST_PLAYWRIGHT_AVAILABLE = True
except ImportError:
    FAST_PLAYWRIGHT_AVAILABLE = False


class FastFoodyPlaywrightScraper(BaseScraper):
    """
    High-performance Foody scraper using Playwright with aggressive optimizations.
    
    Uses fast Playwright driver with disabled images, CSS, and aggressive
    timeouts to minimize scraping time while maintaining data accuracy.
    """
    
    def __init__(self, config, target_url: str):
        """Initialize the fast Foody Playwright scraper."""
        super().__init__(config, target_url)
        
        # Check Playwright availability
        if not FAST_PLAYWRIGHT_AVAILABLE:
            self.logger.error("Fast Playwright not available")
            raise ImportError("Fast Playwright required. Check fast_playwright_utils.py")
        
        # Initialize fast Playwright manager
        self.playwright_manager = None
        self.page = None
        self.fast_mode = True
        
        # Performance tracking
        self.timing_data = {
            'driver_startup': 0,
            'page_load': 0,
            'content_extraction': 0,
            'total_scraping': 0
        }
        
        self.logger.info("Initialized Fast Foody Playwright scraper with aggressive optimizations")
    
    def _setup_browser(self):
        """Setup fast Playwright browser with performance optimizations."""
        start_time = time.time()
        
        try:
            self.playwright_manager = FastPlaywrightManager(
                headless=True,
                timeout=10000,  # 10s timeout instead of 30s
                disable_images=True,
                disable_css=True
            )
            
            self.page = self.playwright_manager.create_fast_driver()
            
            self.timing_data['driver_startup'] = time.time() - start_time
            self.logger.info(f"Fast Playwright driver started in {self.timing_data['driver_startup']:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Failed to setup fast Playwright: {e}")
            raise
    
    def _navigate_to_page(self):
        """Navigate to target page with fast loading."""
        if not self.page:
            self._setup_browser()
            
        start_time = time.time()
        
        try:
            # Fast page fetch with minimal wait
            content = fast_page_fetch(self.page, self.target_url, wait_time=2)
            
            self.timing_data['page_load'] = time.time() - start_time
            self.logger.info(f"Page loaded in {self.timing_data['page_load']:.2f}s: {self.target_url}")
            
        except Exception as e:
            self.logger.error(f"Failed to navigate to page: {e}")
            raise
    
    def extract_restaurant_info(self) -> Dict[str, Any]:
        """Extract restaurant information using fast Playwright."""
        start_time = time.time()
        
        try:
            if not self.page:
                self._setup_browser()
                self._navigate_to_page()
            
            # Fast extraction with minimal waits
            restaurant_info = {
                "name": "",
                "brand": "",
                "address": "",
                "phone": "",
                "rating": 0.0,
                "delivery_fee": 0.0,
                "minimum_order": 0.0,
                "delivery_time": "",
                "cuisine_types": []
            }
            
            # Extract restaurant name with fast selectors
            name_selectors = [
                'h1.restaurant-name',
                'h1[data-testid="restaurant-name"]',
                '.restaurant-header h1',
                'h1'
            ]
            
            for selector in name_selectors:
                element = fast_wait_for_element(self.page, selector, timeout=2000)
                if element:
                    restaurant_info["name"] = fast_get_text_content(element).strip()
                    break
            
            # Extract rating quickly
            rating_selectors = [
                '.rating-value',
                '[data-testid="restaurant-rating"]',
                '.restaurant-rating span'
            ]
            
            for selector in rating_selectors:
                element = fast_wait_for_element(self.page, selector, timeout=1000)
                if element:
                    rating_text = fast_get_text_content(element)
                    try:
                        restaurant_info["rating"] = float(re.search(r'(\d+\.?\d*)', rating_text).group(1))
                    except:
                        pass
                    break
            
            extraction_time = time.time() - start_time
            self.logger.info(f"Fast restaurant info extracted in {extraction_time:.2f}s")
            
            return restaurant_info
            
        except Exception as e:
            self.logger.error(f"Error extracting restaurant info: {e}")
            return {
                "name": "",
                "brand": "",
                "address": "",
                "phone": "",
                "rating": 0.0,
                "delivery_fee": 0.0,
                "minimum_order": 0.0,
                "delivery_time": "",
                "cuisine_types": []
            }
    
    def extract_categories(self) -> List[Dict[str, Any]]:
        """Extract categories using fast Playwright selectors."""
        start_time = time.time()
        
        try:
            if not self.page:
                self._setup_browser()
                self._navigate_to_page()
            
            categories = []
            
            # Fast category extraction
            category_selectors = [
                '.category-item',
                '[data-testid="category"]',
                '.menu-category',
                'h2, h3, h4'
            ]
            
            for selector in category_selectors:
                elements = fast_find_elements(self.page, selector)
                if elements:
                    for i, element in enumerate(elements):
                        text = fast_get_text_content(element).strip()
                        if text and len(text) > 2:  # Valid category name
                            category_id = f"cat_{text.lower().replace(' ', '_').replace('&', 'and')}"
                            category = {
                                "id": category_id,
                                "name": text,
                                "description": f"{text.upper()} items and products",
                                "product_count": 0,
                                "source": "heading",
                                "display_order": i
                            }
                            categories.append(category)
                    break
            
            extraction_time = time.time() - start_time
            self.timing_data['content_extraction'] += extraction_time
            
            self.logger.info(f"Extracted {len(categories)} categories in {extraction_time:.2f}s")
            return categories
            
        except Exception as e:
            self.logger.error(f"Error extracting categories: {e}")
            return []
    
    def extract_products(self) -> List[Dict[str, Any]]:
        """Extract products using fast Playwright with optimized selectors."""
        start_time = time.time()
        
        try:
            if not self.page:
                self._setup_browser()
                self._navigate_to_page()
            
            products = []
            
            # Fast product extraction with primary selector
            primary_selector = 'h3.cc-name_acd53e'
            product_elements = fast_find_elements(self.page, primary_selector)
            
            if product_elements:
                self.logger.info(f"Found {len(product_elements)} valid products using: {primary_selector}")
                
                for i, element in enumerate(product_elements):
                    try:
                        # Fast product data extraction
                        name = fast_get_text_content(element).strip()
                        
                        if name:
                            product = {
                                "id": f"foody_prod_{i + 1}",
                                "name": name,
                                "description": f"Product: {name}",
                                "price": 0.0,
                                "original_price": 0.0,
                                "currency": "EUR",
                                "discount_percentage": 0.0,
                                "category": "Uncategorized",
                                "image_url": "",
                                "availability": True,
                                "options": []
                            }
                            
                            # Fast price extraction from parent container
                            try:
                                parent = element.evaluate("el => el.closest('.menu-item, .product-item, .cc-product')")
                                if parent:
                                    price_element = parent.query_selector('.price, .cc-price, [data-price]')
                                    if price_element:
                                        price_text = fast_get_text_content(price_element)
                                        price_match = re.search(r'(\d+\.?\d*)', price_text.replace(',', '.'))
                                        if price_match:
                                            product["price"] = float(price_match.group(1))
                                            product["original_price"] = product["price"]
                            except:
                                pass
                            
                            products.append(product)
                            
                    except Exception as e:
                        self.logger.warning(f"Error processing product {i}: {e}")
                        continue
            
            extraction_time = time.time() - start_time
            self.timing_data['content_extraction'] += extraction_time
            
            self.logger.info(f"Extracted {len(products)} products in {extraction_time:.2f}s ({extraction_time/max(len(products), 1):.3f}s per product)")
            return products
            
        except Exception as e:
            self.logger.error(f"Error extracting products: {e}")
            return []
    
    def scrape(self) -> Dict[str, Any]:
        """
        Main scraping method with performance tracking.
        
        Returns:
            Complete scraped data with performance metrics
        """
        total_start = time.time()
        
        try:
            self.logger.info(f"Starting fast scrape of: {self.target_url}")
            self.scraped_at = datetime.now(timezone.utc)
            
            # Setup browser
            self._setup_browser()
            
            # Navigate and extract data
            self._navigate_to_page()
            
            # Extract all data with timing and store in base class variables
            extract_start = time.time()
            
            self._restaurant_info = self.extract_restaurant_info()
            self._categories = self.extract_categories()
            self._products = self.extract_products()
            
            self.timing_data['content_extraction'] = time.time() - extract_start
            self.timing_data['total_scraping'] = time.time() - total_start
            
            # Set processing timestamp
            self.processed_at = datetime.now(timezone.utc)
            
            # Generate metadata
            self._metadata = self._generate_metadata()
            
            # Build output with performance data
            output = self._build_output_with_performance()
            
            self.logger.info(f"Fast scraping completed in {self.timing_data['total_scraping']:.2f}s")
            self.logger.info(f"Performance: Driver={self.timing_data['driver_startup']:.2f}s, Page={self.timing_data['page_load']:.2f}s, Extract={self.timing_data['content_extraction']:.2f}s")
            self.logger.info(f"Extracted {len(self._products)} products from {len(self._categories)} categories")
            
            return output
            
        except Exception as e:
            self.logger.error(f"Fast scraping failed: {e}")
            self._add_error("fast_scraping_failed", str(e))
            raise
        finally:
            self._cleanup()
    
    def _build_output_with_performance(self) -> Dict[str, Any]:
        """Build output with performance metrics."""
        # Use parent's build output method
        output = super()._build_output()
        
        # Add performance data to metadata
        if 'metadata' in output:
            output['metadata'].update({
                'performance_mode': 'fast_playwright',
                'timing_breakdown': self.timing_data,
                'optimization_features': [
                    'disabled_images',
                    'disabled_css',
                    'reduced_timeouts',
                    'fast_selectors',
                    'minimal_waits'
                ]
            })
        
        return output
    
    def _cleanup(self):
        """Clean up Playwright resources."""
        try:
            if self.playwright_manager:
                self.playwright_manager.close()
                self.playwright_manager = None
                self.page = None
                self.logger.info("Fast Playwright resources cleaned up")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self._cleanup()
