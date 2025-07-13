"""
Fast Foody.com.cy scraper implementation optimized for performance.

This scraper uses aggressive optimizations to reduce scraping time
while maintaining data quality and extraction accuracy.
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
    from ..common.fast_selenium_utils import FastSeleniumDriver, create_fast_driver
    FAST_SELENIUM_AVAILABLE = True
except ImportError:
    FAST_SELENIUM_AVAILABLE = False


class FastFoodyScraper(BaseScraper):
    """
    High-performance Foody scraper with aggressive optimizations.
    
    Uses fast selenium driver with disabled images, CSS, and aggressive
    timeouts to minimize scraping time while maintaining data accuracy.
    """
    
    def __init__(self, config, target_url: str):
        """Initialize the fast Foody scraper."""
        super().__init__(config, target_url)
        
        # Always use Selenium for JavaScript-heavy sites, but with fast config
        if not FAST_SELENIUM_AVAILABLE:
            self.logger.error("Fast Selenium not available")
            raise ImportError("Fast Selenium required. Check fast_selenium_utils.py")
        
        # Initialize fast selenium driver
        self.selenium_driver = None
        self.fast_mode = True
        
        # Performance tracking
        self.timing_data = {
            'driver_startup': 0,
            'page_load': 0,
            'content_extraction': 0,
            'total_scraping': 0
        }
        
        self.logger.info("Initialized Fast Foody scraper with aggressive optimizations")
        
    def _fetch_page(self) -> BeautifulSoup:
        """
        Fetch and parse the target page using fast Selenium.
        
        Returns:
            BeautifulSoup object of the parsed page
            
        Raises:
            Exception: If page cannot be fetched
        """
        start_time = time.time()
        
        try:
            # Create fast driver with ultra-fast settings
            self.logger.info(f"Starting fast page fetch: {self.target_url}")
            
            driver_start = time.time()
            with create_fast_driver(headless=True, ultra_fast=True) as driver:
                self.timing_data['driver_startup'] = time.time() - driver_start
                
                # Load page with minimal waiting
                page_load_start = time.time()
                success = driver.fast_get_page(
                    self.target_url,
                    wait_for_selector="h3.cc-name_acd53e, .cc-name_acd53e, h3, .menu-item",  # Wait for product names
                    max_wait=15  # Increase timeout to allow JS to load products
                )
                self.timing_data['page_load'] = time.time() - page_load_start
                
                if not success:
                    raise Exception("Failed to load page within timeout")
                
                # Enhanced scroll to trigger lazy loading of products
                driver.fast_scroll_and_wait(scroll_pause=0.5, max_scrolls=4)  # More scrolling for products
                
                # Get soup with fast parsing
                soup = driver.get_fast_soup()
                
                self.timing_data['total_scraping'] = time.time() - start_time
                self.logger.info(f"Fast page fetch completed in {self.timing_data['total_scraping']:.2f}s")
                
                return soup
                
        except Exception as e:
            self.logger.error(f"Fast fetch failed: {e}")
            raise
    
    def extract_restaurant_info(self) -> Dict[str, Any]:
        """
        Fast restaurant information extraction with minimal DOM traversal.
        
        Returns:
            Dictionary containing restaurant information
        """
        if not hasattr(self, '_soup') or not self._soup:
            self.logger.warning("No soup available for restaurant extraction")
            return self._get_default_restaurant_info()
        
        extract_start = time.time()
        
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
        
        try:
            # Fast name extraction using multiple selectors at once
            name_selectors = [
                'h1', '.restaurant-name', '[data-testid="restaurant-name"]',
                '.store-name', '.shop-name', 'title'
            ]
            
            for selector in name_selectors:
                elements = self._soup.select(selector)
                if elements:
                    name = self._clean_text(elements[0].get_text())
                    if name and len(name) > 2:  # Basic validation
                        restaurant_info["name"] = name
                        restaurant_info["brand"] = name  # Use same for brand
                        break
            
            # Fast rating extraction
            rating_selectors = [
                '.rating', '[data-testid="rating"]', '.stars', '.score'
            ]
            
            for selector in rating_selectors:
                element = self._soup.select_one(selector)
                if element:
                    rating_text = element.get_text()
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        try:
                            restaurant_info["rating"] = float(rating_match.group(1))
                            break
                        except ValueError:
                            continue
            
            self.timing_data['restaurant_extraction'] = time.time() - extract_start
            self.logger.debug(f"Restaurant info extracted in {self.timing_data['restaurant_extraction']:.2f}s")
            
        except Exception as e:
            self.logger.warning(f"Error extracting restaurant info: {e}")
        
        return restaurant_info
    
    def _get_default_restaurant_info(self) -> Dict[str, Any]:
        """Get default restaurant info structure."""
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
        """
        Fast category extraction using batch processing.
        
        Returns:
            List of category dictionaries
        """
        if not hasattr(self, '_soup') or not self._soup:
            self.logger.warning("No soup available for category extraction")
            return []
        
        extract_start = time.time()
        categories = []
        
        try:
            # Fast category heading detection
            category_selectors = [
                'h2', 'h3.category', '.menu-section h3', '.category-header',
                '[data-testid="category"]', '.section-title'
            ]
            
            category_elements = []
            for selector in category_selectors:
                elements = self._soup.select(selector)
                if elements:
                    category_elements = elements
                    self.logger.debug(f"Found {len(elements)} categories using: {selector}")
                    break
            
            # Process categories in batch
            for i, element in enumerate(category_elements, 1):
                try:
                    name = self._clean_text(element.get_text())
                    if name and len(name) > 1:
                        category_id = self._generate_category_id(name)
                        
                        category = {
                            "id": category_id,
                            "name": name,
                            "description": f"{name} items and products",
                            "product_count": 0,  # Will be updated later
                            "source": "heading",
                            "display_order": i
                        }
                        categories.append(category)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing category {i}: {e}")
                    continue
            
            self.timing_data['category_extraction'] = time.time() - extract_start
            self.logger.info(f"Extracted {len(categories)} categories in {self.timing_data['category_extraction']:.2f}s")
            
        except Exception as e:
            self.logger.warning(f"Error extracting categories: {e}")
        
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
            # Fast product detection using Foody-specific selectors
            # Based on standard scraper success with 'h3.cc-name_acd53e'
            product_selectors = [
                'h3.cc-name_acd53e',           # Primary Foody selector (confirmed working)
                '.cc-name_acd53e',             # Alternative class match
                'h3[class*="cc-name"]',        # Class pattern match
                'h3',                          # Fallback to all h3 elements
                '.menu-item h3',               # Generic menu item
                '.product-name'                # Product name fallback
            ]
            
            product_elements = []
            selected_selector = None
            
            for selector in product_selectors:
                elements = self._soup.select(selector)
                self.logger.debug(f"Selector '{selector}' found {len(elements)} elements")
                
                if elements and len(elements) >= 2:  # Need at least 2 products
                    # Filter out non-product elements (navigation, headers, etc.)
                    filtered_elements = []
                    for elem in elements:
                        text = elem.get_text(strip=True)
                        # Skip navigation and header elements
                        if text and len(text) > 2 and not any(skip in text.lower() for skip in 
                                ['home', 'delivery', 'about', 'contact', 'menu', 'cart', 'login']):
                            filtered_elements.append(elem)
                    
                    if len(filtered_elements) >= 2:
                        product_elements = filtered_elements
                        selected_selector = selector
                        self.logger.info(f"Found {len(filtered_elements)} valid products using: {selector}")
                        break
            
            if not product_elements:
                self.logger.warning("No products found with any selector")
                # Debug: show what elements are available
                all_h3 = self._soup.select('h3')
                self.logger.debug(f"Total h3 elements found: {len(all_h3)}")
                for i, h3 in enumerate(all_h3[:5]):  # Show first 5
                    self.logger.debug(f"H3 {i+1}: {h3.get_text(strip=True)[:50]}")
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
        Fast single product extraction optimized for Foody structure.
        
        Args:
            element: Product name element (h3.cc-name_acd53e)
            product_id: Unique product identifier
            
        Returns:
            Product dictionary or None if extraction fails
        """
        try:
            # Extract name (we already have the element)
            name = self._clean_text(element.get_text())
            if not name or len(name) < 2:
                return None
            
            # Find product container - Foody wraps products in specific containers
            container = element.find_parent(['div', 'li', 'article', 'section']) or element
            
            # Try to find the actual product card container
            for _ in range(3):  # Go up to 3 levels to find product container
                if container and (container.get('class') or []):
                    classes = ' '.join(container.get('class', []))
                    if any(keyword in classes.lower() for keyword in ['product', 'item', 'card', 'menu']):
                        break
                parent = container.find_parent(['div', 'li', 'article', 'section'])
                if parent:
                    container = parent
                else:
                    break
            
            # Fast price extraction using Foody-specific patterns
            price = 0.0
            
            # Try multiple price selectors in order of likelihood
            price_selectors = [
                '.cc-price',                   # Foody price class
                '[class*="price"]',            # Any price class
                '.price', '.cost', '.amount'   # Generic price selectors
            ]
            
            for price_selector in price_selectors:
                price_element = container.select_one(price_selector)
                if price_element:
                    price_text = price_element.get_text(strip=True)
                    price = self._extract_price_fast(price_text)
                    if price > 0:
                        break
            
            # Fast description extraction
            description = ""
            desc_selectors = [
                '.cc-description',             # Foody description class
                '[class*="description"]',      # Any description class  
                '.description', '.desc', 'p'  # Generic description selectors
            ]
            
            for desc_selector in desc_selectors:
                desc_element = container.select_one(desc_selector)
                if desc_element:
                    description = self._clean_text(desc_element.get_text())
                    if description and len(description) > 5:
                        break
            
            # Fast category assignment - find nearest category header
            category = self._extract_category_fast(element)
            
            # Fast offer name extraction
            offer_name = self._extract_offer_name_fast(container)
            
            # Build product with fast structure
            product = {
                "id": f"foody_prod_{product_id}",
                "name": name,
                "description": description,
                "price": price,
                "original_price": price,
                "currency": "EUR",
                "discount_percentage": 0.0,
                "offer_name": offer_name,  # Add offer name field
                "category": category,
                "image_url": "",  # Skip images for speed
                "availability": True,
                "options": []  # Skip options for speed
            }
            
            return product
            
        except Exception as e:
            self.logger.warning(f"Error in fast product extraction for item {product_id}: {e}")
            return None
            
            # Build product with minimal data
            product = {
                "id": f"foody_prod_{product_id}",
                "name": name,
                "description": description,
                "price": price,
                "original_price": price,
                "currency": "EUR",
                "discount_percentage": 0.0,
                "category": category,
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
    
    def _extract_category_fast(self, container) -> str:
        """
        Fast category extraction from product container.
        
        Args:
            container: Product container element
            
        Returns:
            Category name or "General"
        """
        try:
            # Look for nearest heading element
            for tag in ['h2', 'h3', 'h4']:
                heading = container.find_previous(tag)
                if heading:
                    category_text = self._clean_text(heading.get_text())
                    if category_text and len(category_text) < 50:  # Reasonable category length
                        return category_text
            
            # Fallback to data attributes
            category_attr = container.get('data-category') or container.get('data-section')
            if category_attr:
                return self._clean_text(category_attr)
                
        except Exception:
            pass
        
        return "General"
    
    def _extract_offer_name_fast(self, container) -> str:
        """
        Fast offer name extraction optimized for performance.
        
        Args:
            container: Product container element
            
        Returns:
            Offer name string or empty string if no offer found
        """
        try:
            # Fast offer name extraction - prioritize most common selectors first
            offer_elements = container.select('span.sn-title_522dc0') or container.select('[class*="sn-title"]')
            
            for offer_element in offer_elements:
                offer_text = offer_element.get_text(strip=True)
                
                # Quick checks - skip if empty, too short, or contains %
                if not offer_text or len(offer_text) < 2 or '%' in offer_text:
                    continue
                
                # Quick exclusion of discount patterns 
                if (offer_text.lower().startswith('up to') or 
                    offer_text.lower().endswith('off') or
                    offer_text.startswith('€')):
                    continue
                
                # Valid offer name found
                if 2 <= len(offer_text) <= 50:
                    return offer_text
            
        except Exception:
            pass  # Fail silently for performance
        
        return ""
    
    def scrape(self) -> Dict[str, Any]:
        """
        Execute fast scraping process with performance monitoring.
        
        Returns:
            Dictionary containing all scraped data with timing information
        """
        total_start = time.time()
        
        try:
            self.logger.info(f"Starting fast scrape of: {self.target_url}")
            
            # Fetch page with timing
            self._soup = self._fetch_page()
            
            # Extract data in parallel-optimized way
            content_start = time.time()
            
            # Extract restaurant info
            restaurant_info = self.extract_restaurant_info()
            
            # Extract categories and products
            categories = self.extract_categories()
            products = self.extract_products()
            
            # Update category product counts efficiently
            category_counts = {}
            for product in products:
                cat = product.get('category', 'General')
                category_counts[cat] = category_counts.get(cat, 0) + 1
            
            for category in categories:
                cat_name = category['name']
                category['product_count'] = category_counts.get(cat_name, 0)
            
            self.timing_data['content_extraction'] = time.time() - content_start
            self.timing_data['total_scraping'] = time.time() - total_start
            
            # Build result with matching format to standard scraper
            result = {
                "metadata": {
                    "scraper_version": "1.0.0",  # Match standard scraper version
                    "domain": self.config.domain,
                    "scraping_method": "selenium",  # Keep consistent with standard
                    "requires_javascript": True,
                    "anti_bot_protection": "Basic rate limiting",
                    "url_pattern": self.config.url_pattern,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "processing_duration_seconds": self.timing_data['total_scraping'],
                    "error_count": 0,  # Match standard scraper format
                    "product_count": len(products),
                    "category_count": len(categories)
                },
                "source": {
                    "url": self.target_url,
                    "domain": self.config.domain,
                    "scraped_at": datetime.now(timezone.utc).isoformat()
                },
                "restaurant": restaurant_info,
                "categories": categories,
                "products": products
            }
            
            # Log performance summary (internal only, not in output)
            self.logger.info(f"Fast scraping completed in {self.timing_data['total_scraping']:.2f}s")
            self.logger.info(f"Performance: Driver={self.timing_data['driver_startup']:.2f}s, "
                           f"Page={self.timing_data['page_load']:.2f}s, "
                           f"Extract={self.timing_data['content_extraction']:.2f}s")
            self.logger.info(f"Extracted {len(products)} products, {len(categories)} categories")
            
            # Store performance breakdown internally for CLI display
            result['_internal_performance'] = self.timing_data
            
            return result
            
        except Exception as e:
            self.logger.error(f"Fast scraping failed: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """Fast text cleaning with minimal processing."""
        if not text:
            return ""
        
        # Basic cleaning only
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        return text
    
    def _generate_category_id(self, name: str) -> str:
        """Fast category ID generation."""
        if not name:
            return "cat_general"
        
        # Simple ID generation
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name.lower())
        clean_name = re.sub(r'\s+', '_', clean_name.strip())
        return f"cat_{clean_name}"
