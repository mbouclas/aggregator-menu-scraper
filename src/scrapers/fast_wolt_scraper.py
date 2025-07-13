"""
Fast Wolt scraper implementation optimized for performance.

This scraper uses aggressive optimizations to reduce scraping time
while maintaining data quality for Wolt.com sites.
"""
import time
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional, Tuple
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

from .base_scraper import BaseScraper

# Import fast Selenium utilities for optimized performance
try:
    from ..common.fast_selenium_utils import FastSeleniumDriver
except ImportError:
    FastSeleniumDriver = None


class FastWoltScraper(BaseScraper):
    """
    Fast Wolt scraper with aggressive performance optimizations.
    
    Performance improvements:
    - Disabled images and CSS loading
    - Reduced timeouts (3s implicit, 15s page load)
    - Batch processing for products
    - Optimized DOM traversal
    - Minimal regex operations
    """
    
    def __init__(self, base_url: str = None, verbose: bool = False):
        """
        Initialize fast Wolt scraper with performance optimizations.
        
        Args:
            base_url: Base URL for the scraper
            verbose: Enable verbose logging
        """
        super().__init__(base_url, verbose)
        self.timing_data = {}
        self._soup = None
        
        # Fast driver configuration
        self.driver_options = {
            'headless': True,
            'disable_images': True,
            'disable_css': True,
            'disable_javascript': False,  # Wolt needs JS
            'page_load_timeout': 15,
            'implicit_wait': 3,
            'disable_extensions': True,
            'disable_dev_shm': True
        }
        
        # Performance monitoring
        self.start_time = None
        self.load_time = 0
        self.extraction_time = 0
    
    def setup_driver(self) -> bool:
        """
        Setup fast Selenium driver with aggressive optimizations.
        
        Returns:
            True if setup successful, False otherwise
        """
        setup_start = time.time()
        
        try:
            if FastSeleniumDriver:
                self.driver = FastSeleniumDriver(**self.driver_options)
                self.timing_data['driver_setup'] = time.time() - setup_start
                self.logger.info(f"Fast driver setup in {self.timing_data['driver_setup']:.2f}s")
                return True
            else:
                self.logger.warning("FastSeleniumDriver not available, falling back to standard driver")
                return super().setup_driver()
                
        except Exception as e:
            self.logger.error(f"Failed to setup fast driver: {e}")
            return False
    
    def load_page(self, url: str) -> bool:
        """
        Load page with fast driver and performance monitoring.
        
        Args:
            url: URL to load
            
        Returns:
            True if page loaded successfully
        """
        load_start = time.time()
        self.start_time = load_start
        
        try:
            if not self.driver:
                if not self.setup_driver():
                    return False
            
            self.logger.info(f"Loading page with fast driver: {url}")
            self.driver.get(url)
            
            # Fast page load verification
            title = self.driver.title
            if not title or "error" in title.lower():
                self.logger.warning(f"Potential page load issue: {title}")
                return False
            
            self.load_time = time.time() - load_start
            self.timing_data['page_load'] = self.load_time
            
            self.logger.info(f"Page loaded in {self.load_time:.2f}s")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading page: {e}")
            return False
    
    def get_page_content(self) -> BeautifulSoup:
        """
        Get page content with fast parsing and caching.
        
        Returns:
            BeautifulSoup object
        """
        if self._soup:
            return self._soup
        
        parse_start = time.time()
        
        try:
            page_source = self.driver.page_source
            # Use lxml parser for faster parsing
            self._soup = BeautifulSoup(page_source, 'lxml')
            
            parse_time = time.time() - parse_start
            self.timing_data['content_parsing'] = parse_time
            
            self.logger.info(f"Content parsed in {parse_time:.2f}s")
            return self._soup
            
        except Exception as e:
            self.logger.error(f"Error parsing page content: {e}")
            return BeautifulSoup("", 'html.parser')
    
    def extract_restaurant_info(self) -> Dict[str, Any]:
        """
        Fast restaurant information extraction for Wolt.
        
        Returns:
            Dictionary containing restaurant information
        """
        if not hasattr(self, '_soup') or not self._soup:
            self.logger.warning("No soup available for restaurant info extraction")
            return {}
        
        extract_start = time.time()
        
        try:
            # Fast restaurant name extraction
            name_selectors = [
                'h1[data-test-id="venue-info-header-name"]',  # Primary Wolt selector
                'h1.venue-name',
                '.restaurant-name h1',
                'h1[class*="name"]',
                'h1'  # Fallback
            ]
            
            restaurant_name = ""
            for selector in name_selectors:
                element = self._soup.select_one(selector)
                if element:
                    restaurant_name = element.get_text(strip=True)
                    if restaurant_name:
                        break
            
            # Fast address extraction
            address_selectors = [
                '[data-test-id="venue-info-header-address"]',
                '.venue-address',
                '.restaurant-address',
                '.address'
            ]
            
            address = ""
            for selector in address_selectors:
                element = self._soup.select_one(selector)
                if element:
                    address = element.get_text(strip=True)
                    if address:
                        break
            
            # Fast rating extraction
            rating = 0.0
            rating_selectors = [
                '[data-test-id="venue-info-rating"]',
                '.rating-value',
                '.venue-rating',
                '.rating'
            ]
            
            for selector in rating_selectors:
                element = self._soup.select_one(selector)
                if element:
                    rating_text = element.get_text(strip=True)
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        try:
                            rating = float(rating_match.group(1))
                            break
                        except ValueError:
                            continue
            
            info = {
                'name': restaurant_name,
                'address': address,
                'phone': '',
                'website': self.current_url if hasattr(self, 'current_url') else '',
                'rating': rating,
                'cuisine_type': 'Restaurant',
                'opening_hours': {},
                'description': ''
            }
            
            extraction_time = time.time() - extract_start
            self.timing_data['restaurant_info_extraction'] = extraction_time
            
            self.logger.info(f"Restaurant info extracted in {extraction_time:.2f}s")
            return info
            
        except Exception as e:
            self.logger.error(f"Error extracting restaurant info: {e}")
            return {}
    
    def extract_categories(self) -> List[Dict[str, Any]]:
        """
        Fast category extraction with optimized selectors.
        
        Returns:
            List of category dictionaries
        """
        if not hasattr(self, '_soup') or not self._soup:
            self.logger.warning("No soup available for category extraction")
            return []
        
        extract_start = time.time()
        categories = []
        
        try:
            # Fast category detection using multiple selectors
            category_selectors = [
                '[data-test-id="horizontal-item-card-header"]',  # Primary Wolt selector
                '.category-name',
                '.menu-category h2',
                '.section-header h2',
                'h2[class*="category"]',
                'h2[class*="section"]'
            ]
            
            found_categories = set()  # Avoid duplicates
            
            for selector in category_selectors:
                elements = self._soup.select(selector)
                if elements:
                    for i, element in enumerate(elements):
                        category_name = element.get_text(strip=True)
                        if category_name and len(category_name) > 1 and category_name not in found_categories:
                            found_categories.add(category_name)
                            categories.append({
                                'id': f'wolt_cat_{len(categories) + 1}',
                                'name': category_name,
                                'description': f'Category: {category_name}',
                                'image_url': ''
                            })
                    break  # Use first successful selector
            
            # Fallback if no categories found
            if not categories:
                categories.append({
                    'id': 'wolt_cat_general',
                    'name': 'General',
                    'description': 'General category',
                    'image_url': ''
                })
            
            extraction_time = time.time() - extract_start
            self.timing_data['category_extraction'] = extraction_time
            
            self.logger.info(f"Extracted {len(categories)} categories in {extraction_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error in category extraction: {e}")
        
        return categories
    
    def extract_products(self) -> List[Dict[str, Any]]:
        """
        Fast product extraction with optimized DOM traversal.
        
        Returns:
            List of product dictionaries
        """
        if not hasattr(self, '_soup') or not self._soup:
            self.logger.warning("No soup available for product extraction")
            return []
        
        extract_start = time.time()
        products = []
        
        try:
            # Fast product detection using multiple selectors
            product_selectors = [
                '[data-test-id="horizontal-item-card"]',     # Primary Wolt selector
                '[data-test-id="item-card"]',                # Alternative Wolt selector
                '.menu-item',                                # Generic menu item
                '.product-card',                             # Product card
                '.item-card',                                # Item card
                '[class*="item"][class*="card"]'             # Any item card class
            ]
            
            product_elements = []
            selected_selector = None
            
            for selector in product_selectors:
                elements = self._soup.select(selector)
                if elements and len(elements) > 2:  # Need multiple products
                    product_elements = elements
                    selected_selector = selector
                    self.logger.info(f"Found {len(elements)} products using: {selector}")
                    break
            
            if not product_elements:
                self.logger.warning("No products found with any selector")
                return products
            
            # Batch process products for efficiency
            batch_size = 50  # Process in chunks for memory efficiency
            total_products = len(product_elements)
            
            for batch_start in range(0, total_products, batch_size):
                batch_end = min(batch_start + batch_size, total_products)
                batch_elements = product_elements[batch_start:batch_end]
                
                for i, element in enumerate(batch_elements, batch_start + 1):
                    try:
                        product = self._extract_single_product_fast(element, i)
                        if product:
                            products.append(product)
                            
                    except Exception as e:
                        self.logger.warning(f"Error extracting product {i}: {e}")
                        continue
            
            extraction_time = time.time() - extract_start
            self.timing_data['product_extraction'] = extraction_time
            
            self.logger.info(f"Extracted {len(products)} products in {extraction_time:.2f}s "
                           f"({extraction_time/len(products):.3f}s per product)")
            
        except Exception as e:
            self.logger.error(f"Error in product extraction: {e}")
        
        return products
    
    def _extract_single_product_fast(self, element, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Fast single product extraction with minimal DOM queries.
        
        Args:
            element: Product container element
            product_id: Unique product identifier
            
        Returns:
            Product dictionary or None if extraction fails
        """
        try:
            # Extract name quickly
            name_selectors = [
                '[data-test-id="horizontal-item-card-header"]',
                '.item-name',
                '.product-name',
                'h3', 'h4'
            ]
            
            name = ""
            for selector in name_selectors:
                name_element = element.select_one(selector)
                if name_element:
                    name = self._clean_text(name_element.get_text())
                    if name:
                        break
            
            if not name or len(name) < 2:
                return None
            
            # Fast price extraction
            price_selectors = [
                '[data-test-id="horizontal-item-card-price"]',
                '.price',
                '.cost',
                '.amount',
                '[class*="price"]'
            ]
            
            price = 0.0
            for selector in price_selectors:
                price_element = element.select_one(selector)
                if price_element:
                    price = self._extract_price_fast(price_element.get_text())
                    if price > 0:
                        break
            
            # Fast description extraction
            desc_selectors = [
                '[data-test-id="horizontal-item-card-description"]',
                '.description',
                '.item-description',
                'p'
            ]
            
            description = ""
            for selector in desc_selectors:
                desc_element = element.select_one(selector)
                if desc_element:
                    description = self._clean_text(desc_element.get_text())
                    if description:
                        break
            
            # Build product with minimal data
            product = {
                "id": f"wolt_prod_{product_id}",
                "name": name,
                "description": description,
                "price": price,
                "original_price": price,
                "currency": "EUR",
                "discount_percentage": 0.0,
                "category": "General",
                "image_url": "",  # Skip images for speed
                "availability": True,
                "options": []  # Skip options for speed
            }
            
            return product
            
        except Exception as e:
            self.logger.warning(f"Error in fast product extraction for item {product_id}: {e}")
            return None
    
    def _extract_price_fast(self, price_text: str) -> float:
        """
        Fast price extraction using optimized regex.
        
        Args:
            price_text: Text containing price information
            
        Returns:
            Extracted price as float
        """
        if not price_text:
            return 0.0
        
        try:
            # Single regex for common price patterns
            price_match = re.search(r'[€$£]?[\d,]+\.?\d*', price_text.replace(',', '.'))
            if price_match:
                price_str = price_match.group()
                # Remove currency symbols
                price_str = re.sub(r'[€$£]', '', price_str)
                return float(price_str)
        except (ValueError, AttributeError):
            pass
        
        return 0.0
    
    def _clean_text(self, text: str) -> str:
        """
        Fast text cleaning with minimal operations.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Single regex for whitespace normalization
        cleaned = re.sub(r'\s+', ' ', text.strip())
        return cleaned
    
    def scrape(self) -> Dict[str, Any]:
        """
        Execute fast scraping process with performance monitoring.
        
        Returns:
            Dictionary containing all scraped data with timing information
        """
        scrape_start = time.time()
        
        try:
            # Get content once and cache it
            soup = self.get_page_content()
            if not soup or not soup.find():
                self.logger.error("Failed to get page content")
                return {}
            
            # Extract all data using cached soup
            restaurant_info = self.extract_restaurant_info()
            categories = self.extract_categories()
            products = self.extract_products()
            
            total_time = time.time() - scrape_start
            
            result = {
                'restaurant_info': restaurant_info,
                'categories': categories,
                'products': products,
                'scraping_metadata': {
                    'scraper_type': 'FastWoltScraper',
                    'total_time': total_time,
                    'products_count': len(products),
                    'categories_count': len(categories),
                    'performance_data': self.timing_data,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            }
            
            self.logger.info(f"Fast scraping completed in {total_time:.2f}s")
            self.logger.info(f"Performance breakdown: {self.timing_data}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in fast scraping process: {e}")
            return {}
    
    def cleanup(self):
        """
        Clean up resources and log performance summary.
        """
        if hasattr(self, 'start_time') and self.start_time:
            total_session_time = time.time() - self.start_time
            self.logger.info(f"Fast scraper session completed in {total_session_time:.2f}s")
        
        super().cleanup()
    
    def _extract_offer_name_fast(self, element) -> str:
        """
        Fast offer name extraction for Wolt products.
        
        Args:
            element: Product container element
            
        Returns:
            Offer name or empty string if no offer found
        """
        try:
            # Look for offer span within the product element
            offer_span = element.select_one('span.byr4db3')
            if offer_span:
                offer_text = self._clean_text(offer_span.get_text())
                # Validate: not empty, reasonable length
                if offer_text and 3 <= len(offer_text) <= 200:
                    return offer_text
            
            return ""
            
        except Exception:
            return ""
