"""
Wolt.com scraper implementation.

This scraper extracts restaurant and menu data from wolt.com
using Playwright for JavaScript-heavy content handling.
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional, Tuple
import re
import time
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

from .base_scraper import BaseScraper

# No longer need Selenium imports - Playwright is handled through base class


class WoltScraper(BaseScraper):
    """
    Scraper implementation for wolt.com
    
    Supports both requests+BeautifulSoup and Selenium scraping methods
    based on configuration. Automatically detects JavaScript requirements
    and switches to Selenium when needed.
    """
    
    def __init__(self, config, target_url: str):
        """Initialize the Wolt scraper."""
        super().__init__(config, target_url)
        
        # Determine scraping method from config
        self.scraping_method = getattr(config, 'scraping_method', 'selenium').lower()
        
        # Wolt always requires JavaScript, so we always use Playwright
        # If the config specifies Selenium or requires JavaScript, we now use Playwright
        if self.scraping_method == 'selenium' or self.config.requires_javascript:
            self.scraping_method = 'playwright'
            self.logger.info("Using Playwright for JavaScript-enabled scraping (Wolt requires JS)")
        else:
            # Still initialize requests for potential fallback
            self._init_requests()
            # But warn that Wolt needs JavaScript
            self.logger.warning("Wolt typically requires JavaScript - Playwright recommended")
    
    def _init_requests(self):
        """Initialize requests-based scraping."""
        self.session = requests.Session()
        
        # Set user agent to avoid basic bot detection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Set timeout and retry settings
        self.timeout = 30
        self.max_retries = 3
    

        
    def _fetch_page(self) -> BeautifulSoup:
        """
        Fetch and parse the target page using the configured method.
        
        Returns:
            BeautifulSoup object of the parsed page
            
        Raises:
            Exception: If page cannot be fetched after retries
        """
        if self.scraping_method == 'playwright':
            return self._fetch_page_playwright()
        else:
            return self._fetch_page_requests()
    
    def _fetch_page_requests(self) -> BeautifulSoup:
        """
        Fetch page using requests + BeautifulSoup.
        
        Returns:
            BeautifulSoup object of the parsed page
        """
        self.logger.info(f"Fetching page with requests: {self.target_url}")
        
        for attempt in range(self.max_retries):
            try:
                # Add delay for rate limiting
                if attempt > 0:
                    delay = 2 ** attempt  # Exponential backoff
                    self.logger.info(f"Retry attempt {attempt + 1}, waiting {delay}s")
                    time.sleep(delay)
                
                response = self.session.get(self.target_url, timeout=self.timeout)
                response.raise_for_status()
                
                self.logger.debug(f"Page fetched successfully, status: {response.status_code}")
                self.logger.debug(f"Content length: {len(response.content)} bytes")
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Basic validation - check if page has expected structure
                if not soup.find('html'):
                    raise ValueError("Invalid HTML structure")
                
                return soup
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    self._add_error("fetch_failed", f"Failed to fetch page after {self.max_retries} attempts: {str(e)}")
                    raise
            
            except Exception as e:
                self.logger.error(f"Unexpected error fetching page: {e}")
                self._add_error("fetch_error", str(e))
                raise
    
    def _fetch_page_playwright(self) -> BeautifulSoup:
        """
        Fetch page using Playwright (base class handles browser management).
        
        Returns:
            BeautifulSoup object of the parsed page
        """
        self.logger.info(f"Fetching page with Playwright: {self.target_url}")
        
        try:
            # Page should already be loaded by base class
            if not self.page:
                self.logger.error("Playwright page not initialized")
                # Fallback to requests
                return self._fetch_page_requests()
            
            # Wait for specific Wolt content to load
            try:
                # Wait for product content - use multiple possible selectors
                self.wait_for_selector('h3[data-test-id="horizontal-item-card-header"], h3[class*="tj9y"], h3', timeout=15000)
            except Exception as e:
                self.logger.warning(f"Timeout waiting for product content: {e}")
            
            # Scroll to load any lazy-loaded content (Wolt uses infinite scroll)
            for _ in range(3):  # Scroll multiple times for Wolt's infinite scroll
                self.scroll_page_to_bottom()
                self.page.wait_for_timeout(1500)  # Give time for content to load
            
            # Get the page content
            page_content = self.page.content()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_content, 'html.parser')
            
            self.logger.debug(f"Playwright page loaded, content length: {len(page_content)}")
            return soup
                
        except Exception as e:
            self.logger.error(f"Playwright page fetch failed: {e}")
            self._add_error("playwright_fetch_failed", f"Failed to fetch page with Playwright: {str(e)}")
            
            # Fallback to requests if Playwright fails
            self.logger.info("Falling back to requests method")
            return self._fetch_page_requests()

    def extract_restaurant_info(self) -> Dict[str, Any]:
        """
        Extract restaurant information from the page.
        
        Returns:
            Dictionary containing restaurant information
        """
        self.logger.info("Extracting restaurant information")
        
        # Default restaurant info structure
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
            # Fetch the page
            soup = self._fetch_page()
            
            # Extract restaurant name using Wolt-specific selectors
            restaurant_name = self._extract_restaurant_name(soup)
            if restaurant_name:
                restaurant_info["name"] = restaurant_name
                self.logger.debug(f"Extracted restaurant name: {restaurant_name}")
            else:
                self._add_error("restaurant_name_missing", "Could not extract restaurant name")
            
            # Extract brand name from image alt attribute
            brand_name = self._extract_brand_name(soup)
            if brand_name:
                restaurant_info["brand"] = brand_name
                self.logger.debug(f"Extracted brand name: {brand_name}")
            else:
                restaurant_info["brand"] = restaurant_name  # Use restaurant name as fallback
            
            # Try to extract additional info (these may not be available without JavaScript)
            self._extract_additional_restaurant_info(soup, restaurant_info)
            
            return restaurant_info
            
        except Exception as e:
            self.logger.error(f"Failed to extract restaurant info: {e}")
            self._add_error("restaurant_extraction_failed", str(e))
            return restaurant_info
    
    def _extract_restaurant_name(self, soup: BeautifulSoup) -> str:
        """
        Extract restaurant name using Wolt-specific selectors.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Restaurant name or empty string if not found
        """
        # Strategy 1: Look for Wolt-specific venue title
        selectors = [
            'span[data-test-id="venue-hero.venue-title"]',  # Primary Wolt selector
            'h1 span[data-test-id="venue-hero.venue-title"]',  # With h1 wrapper
            'h1.habto2o span',  # With specific class
            'h1[class*="habto"]',  # Any h1 with habto class
            'h1',  # Generic h1 fallback
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                self.logger.debug(f"Selector '{selector}' found {len(elements)} elements")
                
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 2:  # Basic validation
                        self.logger.debug(f"Found restaurant name with '{selector}': {text}")
                        return text
                        
            except Exception as e:
                self.logger.debug(f"Selector '{selector}' failed: {e}")
        
        return ""
    
    def _extract_brand_name(self, soup: BeautifulSoup) -> str:
        """
        Extract brand name from image alt attribute.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Brand name or empty string if not found
        """
        try:
            # Look for images with alt attribute containing brand name
            img_selectors = [
                'img.s1siin91',  # Specific Wolt image class
                'img[alt]',  # Any image with alt attribute
            ]
            
            for selector in img_selectors:
                images = soup.select(selector)
                for img in images:
                    alt_text = img.get('alt', '').strip()
                    # Filter out common non-brand alt texts
                    if alt_text and len(alt_text) > 2 and not any(skip in alt_text.lower() for skip in ['logo', 'icon', 'image', 'photo']):
                        self.logger.debug(f"Found brand name from image alt: {alt_text}")
                        return alt_text
                        
        except Exception as e:
            self.logger.debug(f"Brand name extraction failed: {e}")
        
        return ""
    
    def _extract_additional_restaurant_info(self, soup: BeautifulSoup, restaurant_info: Dict[str, Any]):
        """Extract additional restaurant information if available."""
        try:
            # This method can be extended to extract rating, delivery info, etc.
            # For now, we'll leave it as a placeholder
            pass
        except Exception as e:
            self.logger.debug(f"Additional info extraction failed: {e}")

    def extract_categories(self) -> List[Dict[str, Any]]:
        """
        Extract category information using Wolt-specific methods.
        
        Returns:
            List of category dictionaries
        """
        self.logger.info("Extracting categories using wolt.com specific methods")
        
        try:
            soup = self._fetch_page()
            categories = []
            
            # Check if page requires JavaScript (affects category availability)
            js_indicators = self._detect_javascript_requirements(soup)
            if js_indicators:
                # Only warn if we're not using Playwright (which handles JavaScript)
                if self.scraping_method != 'playwright':
                    self.logger.warning(f"Page requires JavaScript for dynamic content: {js_indicators}")
                    self._add_error("javascript_required_categories", 
                                  f"Category extraction limited due to JavaScript requirements: {', '.join(js_indicators)}")
                else:
                    # With Playwright, just log as debug since we're handling JavaScript
                    self.logger.debug(f"JavaScript detected (handled by Playwright): {js_indicators}")
                    # Still record as info for transparency but don't treat as error
                    self._add_error("javascript_detected_playwright", 
                                  f"JavaScript content detected (handled by Playwright): {', '.join(js_indicators)}")
            
            # Strategy 1: Extract from h2 headings (primary method for Wolt)
            categories.extend(self._extract_categories_from_headings(soup))
            
            # If we have categories, clean and process them
            if categories:
                # Remove duplicates and clean names
                seen_names = set()
                cleaned_categories = []
                
                for cat in categories:
                    clean_name = self._clean_wolt_category_name(cat['name'])
                    if clean_name and clean_name.lower() not in seen_names:
                        cat['name'] = clean_name
                        cat['id'] = self._generate_category_id(clean_name)
                        cleaned_categories.append(cat)
                        seen_names.add(clean_name.lower())
                
                categories = cleaned_categories
                self.logger.info(f"Extracted {len(categories)} categories")
            else:
                self.logger.info("Using fallback categories due to JavaScript requirements")
                categories = self._get_fallback_categories()
            
            return categories
            
        except Exception as e:
            self.logger.error(f"Category extraction failed: {e}")
            self._add_error("category_extraction_failed", str(e))
            return self._get_fallback_categories()

    def _extract_categories_from_headings(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract categories from h2 heading elements (Wolt-specific)."""
        categories = []
        
        try:
            # Look for h2 elements with Wolt-specific classes
            heading_selectors = [
                'h2.h129y4wz',  # Primary Wolt category selector
                'h2[class*="h129"]',  # Variation of the class
                'h2',  # Generic h2 fallback
            ]
            
            for selector in heading_selectors:
                elements = soup.select(selector)
                self.logger.debug(f"Found {len(elements)} elements with selector '{selector}'")
                
                for element in elements:
                    category_text = element.get_text(strip=True)
                    if self._is_valid_wolt_category_text(category_text):
                        categories.append(self._create_category_dict(category_text, "heading"))
                        
                        if len(categories) >= 15:  # Reasonable limit
                            break
                
                if len(categories) >= 15:
                    break
                    
        except Exception as e:
            self.logger.debug(f"Heading category extraction failed: {e}")
        
        return categories
    
    def _is_valid_wolt_category_text(self, text: str) -> bool:
        """
        Check if text looks like a valid Wolt category name.
        
        Args:
            text: Text to validate
            
        Returns:
            True if text appears to be a category name
        """
        if not text or len(text.strip()) < 2:
            return False
        
        text = text.strip().upper()
        
        # Skip common non-category texts
        skip_patterns = [
            'MENU', 'RESTAURANT', 'DELIVERY', 'ORDER', 'CART', 'CHECKOUT',
            'POPULAR', 'RECOMMENDED', 'FEATURED', 'NEW', 'SPECIAL',
            'ITEM', 'PRODUCT', 'DESCRIPTION', 'PRICE', 'ALLERGEN'
        ]
        
        for pattern in skip_patterns:
            if pattern in text:
                return False
        
        # Valid if it's a reasonable length and contains letters
        return 2 <= len(text) <= 50 and any(c.isalpha() for c in text)
    
    def _clean_wolt_category_name(self, name: str) -> str:
        """
        Clean and normalize Wolt category name.
        
        Args:
            name: Raw category name
            
        Returns:
            Cleaned category name
        """
        if not name:
            return ""
        
        # Remove emojis and special characters as specified in config
        clean_name = re.sub(r'[🆕🌶️🍔🥤🍕🍰🥗🍜🍲🔥⭐🎉🎊]', '', name)
        
        # Remove numbers at the start (e.g., "1. STARTERS" -> "STARTERS")
        clean_name = re.sub(r'^\d+\.\s*', '', clean_name)
        
        # Clean whitespace and convert to title case
        clean_name = ' '.join(clean_name.split()).title()
        
        return clean_name
    
    def _get_fallback_categories(self) -> List[Dict[str, Any]]:
        """
        Get fallback categories when extraction fails.
        
        Returns:
            List of fallback category dictionaries
        """
        fallback_categories = [
            "Starters", "Mains", "Desserts", "Drinks", "Extras",
            "Hot Dishes", "Cold Dishes", "Salads", "Sides", "Specials"
        ]
        
        categories = []
        for i, cat_name in enumerate(fallback_categories):
            categories.append(self._create_category_dict(cat_name, "fallback", i))
        
        return categories

    def extract_products(self) -> List[Dict[str, Any]]:
        """
        Extract product information using Wolt-specific selectors.
        
        Returns:
            List of product dictionaries
        """
        self.logger.info("Extracting products using wolt.com selectors")
        
        try:
            soup = self._fetch_page()
            products = []
            
            # Check if page requires JavaScript (common indicators)
            js_indicators = self._detect_javascript_requirements(soup)
            if js_indicators:
                # Only warn if we're not using Playwright (which handles JavaScript)
                if self.scraping_method != 'playwright':
                    self.logger.warning(f"Page appears to require JavaScript: {js_indicators}")
                    self._add_error("javascript_required", 
                                  f"Page requires JavaScript for dynamic content loading. Found indicators: {', '.join(js_indicators)}")
                else:
                    # With Playwright, just log as debug since we're handling JavaScript
                    self.logger.debug(f"JavaScript detected (handled by Playwright): {js_indicators}")
                    # Record as info but not an error since Playwright handles it
                    self._add_error("javascript_detected_playwright", 
                                  f"JavaScript content detected (handled by Playwright): {', '.join(js_indicators)}")
            
            # Use Wolt-specific selectors from configuration
            product_title_selectors = [
                'h3[data-test-id="horizontal-item-card-header"]',  # Primary Wolt selector
                'h3.tj9ydql',  # With specific class
                'h3[class*="tj9y"]',  # Variation of the class
                '[data-test-id*="item-card-header"]',  # Alternative test ID
                'h3',  # Generic h3 fallback
            ]
            
            self.logger.debug("Searching for products with wolt.com selectors")
            
            for selector in product_title_selectors:
                try:
                    title_elements = soup.select(selector)
                    self.logger.debug(f"Found {len(title_elements)} elements with selector '{selector}'")
                    
                    if title_elements:
                        # Process each product title element
                        for i, title_element in enumerate(title_elements):
                            try:
                                product_data = self._extract_single_wolt_product(title_element, i + 1)
                                if product_data:
                                    products.append(product_data)
                                    self.logger.debug(f"Extracted product: {product_data['name']} - €{product_data['price']}")
                                
                            except Exception as e:
                                self.logger.warning(f"Failed to extract product {i+1}: {e}")
                                self._add_error("product_extraction_error", f"Product {i+1}: {str(e)}", {"selector": selector, "index": i})
                        
                        # If we found products with this selector, stop trying others
                        if products:
                            self.logger.info(f"Successfully extracted {len(products)} products using selector '{selector}'")
                            break
                            
                except Exception as e:
                    self.logger.debug(f"Selector '{selector}' failed: {e}")
            
            # If no products found, try to extract any text that looks like product information
            if not products:
                self.logger.info("No products found with CSS selectors, trying text-based extraction")
                products = self._try_text_based_product_extraction(soup)
                
                if products:
                    self.logger.info(f"Extracted {len(products)} products using text-based fallback")
                    self._add_error("text_based_extraction_used", 
                                  f"Used fallback text extraction due to JavaScript requirements. Found {len(products)} price patterns.")
                else:
                    error_msg = "Could not find products using any configured selector"
                    if js_indicators:
                        if self.scraping_method == 'playwright':
                            error_msg += ". Page uses JavaScript for dynamic content (Playwright is handling this, but selectors may need adjustment)"
                        else:
                            error_msg += ". Page requires JavaScript for dynamic content - consider using Playwright instead of requests+BeautifulSoup"
                    
                    self._add_error("no_products_found", error_msg, {"javascript_required": bool(js_indicators)})
            
            return products
            
        except Exception as e:
            self.logger.error(f"Product extraction failed: {e}")
            self._add_error("product_extraction_failed", str(e))
            return []

    def _extract_single_wolt_product(self, title_element, index: int) -> Optional[Dict[str, Any]]:
        """
        Extract product information from a single Wolt product element.
        
        Args:
            title_element: BeautifulSoup element containing product title
            index: Product index for unique ID generation
            
        Returns:
            Product dictionary or None if extraction fails
        """
        try:
            # Extract product name
            product_name = title_element.get_text(strip=True)
            if not product_name:
                return None
            
            # Clean product name (remove emojis as specified)
            clean_name = self._clean_wolt_product_name(product_name)
            
            # Find the parent container that might contain price and other info
            product_container = title_element
            for _ in range(5):  # Look up to 5 levels up
                product_container = product_container.parent
                if not product_container:
                    break
                
                # Check if this container has price information
                if product_container.find(attrs={'data-test-id': re.compile('price')}):
                    break
            
            # Extract price information
            price_info = self._extract_wolt_price_info(product_container or title_element)
            
            # Try to find category from nearest h2 parent
            category = self._find_product_category(title_element)
            
            # Extract offer name for this product
            self.logger.debug(f"Extracting offer for product: '{clean_name}'")
            offer_name = self._extract_offer_name_wolt(product_container or title_element)
            self.logger.debug(f"Extracted offer name: '{offer_name}' for product: '{clean_name}'")
            
            # Create product dictionary
            product = {
                "id": f"wolt_prod_{index}",
                "name": clean_name,
                "description": f"Product: {clean_name}",
                "price": price_info.get('price', 0.0),
                "original_price": price_info.get('original_price', price_info.get('price', 0.0)),
                "currency": "EUR",
                "discount_percentage": price_info.get('discount_percentage', 0.0),
                "offer_name": offer_name,  # Add offer name field
                "category": category,
                "image_url": "",
                "availability": True,
                "options": []
            }
            
            return product
            
        except Exception as e:
            self.logger.debug(f"Failed to extract product {index}: {e}")
            return None
    
    def _clean_wolt_product_name(self, name: str) -> str:
        """
        Clean Wolt product name by removing emojis and numbers.
        
        Args:
            name: Raw product name
            
        Returns:
            Cleaned product name
        """
        if not name:
            return ""
        
        # Remove emojis as specified in config
        clean_name = re.sub(r'[🆕🌶️🍔🥤🍕🍰🥗🍜🍲🔥⭐🎉🎊]', '', name)
        
        # Remove leading numbers and dots (e.g., "104. Edamame" -> "Edamame")
        clean_name = re.sub(r'^\d+\.\s*', '', clean_name)
        
        # Clean extra whitespace
        clean_name = ' '.join(clean_name.split())
        
        return clean_name.strip()
    
    def _extract_wolt_price_info(self, container) -> Dict[str, float]:
        """
        Extract price information from Wolt product container.
        
        Args:
            container: BeautifulSoup element containing price info
            
        Returns:
            Dictionary with price information
        """
        price_info = {
            'price': 0.0,
            'original_price': 0.0,
            'discount_percentage': 0.0
        }
        
        try:
            # Look for discounted price (primary price)
            discounted_price_elem = container.find(attrs={'data-test-id': 'horizontal-item-card-discounted-price'})
            if discounted_price_elem:
                aria_label = discounted_price_elem.get('aria-label', '')
                price_match = re.search(r'€(\d+[.,]\d+)', aria_label)
                if price_match:
                    price_info['price'] = float(price_match.group(1).replace(',', '.'))
            
            # Look for original price (if there's a discount)
            original_price_elem = container.find(attrs={'data-test-id': 'horizontal-item-card-original-price'})
            if original_price_elem:
                aria_label = original_price_elem.get('aria-label', '')
                price_match = re.search(r'(\d+[.,]\d+)', aria_label)
                if price_match:
                    original_price = float(price_match.group(1).replace(',', '.'))
                    price_info['original_price'] = original_price
                    
                    # Calculate discount percentage
                    if price_info['price'] > 0 and original_price > price_info['price']:
                        discount = ((original_price - price_info['price']) / original_price) * 100
                        price_info['discount_percentage'] = round(discount, 1)
            
            # If no discounted price found, look for regular price
            if price_info['price'] == 0.0:
                # Look for any price element
                price_elements = container.find_all(text=re.compile(r'€\d+[.,]\d+'))
                for elem in price_elements:
                    price_match = re.search(r'€(\d+[.,]\d+)', elem)
                    if price_match:
                        price_info['price'] = float(price_match.group(1).replace(',', '.'))
                        price_info['original_price'] = price_info['price']
                        break
            
            # Set original_price to price if not set
            if price_info['original_price'] == 0.0:
                price_info['original_price'] = price_info['price']
                
        except Exception as e:
            self.logger.debug(f"Price extraction failed: {e}")
        
        return price_info
    
    def _find_product_category(self, product_element) -> str:
        """
        Find the category for a product by looking for the nearest h2 parent.
        
        Args:
            product_element: BeautifulSoup element of the product
            
        Returns:
            Category name or "Uncategorized"
        """
        try:
            # Walk up the DOM tree to find the nearest h2 with category
            current = product_element
            for _ in range(10):  # Look up to 10 levels up
                if not current:
                    break
                
                # Look for h2 elements in current level or siblings
                h2_elements = current.find_all('h2', class_='h129y4wz') if hasattr(current, 'find_all') else []
                
                if h2_elements:
                    for h2 in h2_elements:
                        category_text = h2.get_text(strip=True)
                        if category_text and self._is_valid_wolt_category_text(category_text):
                            return self._clean_wolt_category_name(category_text)
                
                # Look for h2 in previous siblings
                if hasattr(current, 'find_previous'):
                    prev_h2 = current.find_previous('h2', class_='h129y4wz')
                    if prev_h2:
                        category_text = prev_h2.get_text(strip=True)
                        if category_text and self._is_valid_wolt_category_text(category_text):
                            return self._clean_wolt_category_name(category_text)
                
                current = current.parent
                
        except Exception as e:
            self.logger.debug(f"Category finding failed: {e}")
        
        return "Uncategorized"

    def _detect_javascript_requirements(self, soup: BeautifulSoup) -> List[str]:
        """
        Detect if the page requires JavaScript for content loading.
        
        Args:
            soup: BeautifulSoup parsed page
            
        Returns:
            List of indicators that suggest JavaScript is required
        """
        indicators = []
        
        try:
            # Check for loading/skeleton/spinner elements
            loading_classes = ['loading', 'spinner', 'skeleton', 'placeholder']
            for class_name in loading_classes:
                elements = soup.find_all(class_=re.compile(class_name, re.IGNORECASE))
                if elements:
                    indicators.append(f"{len(elements)} {class_name} elements")
            
            # Check for modern JS framework indicators
            js_frameworks = ['react', 'vue', 'angular', 'app-root', 'ng-app']
            for framework in js_frameworks:
                elements = soup.find_all(class_=re.compile(framework, re.IGNORECASE))
                if elements:
                    indicators.append(f"{framework} framework")
            
            # Check script tag count (high count suggests heavy JS usage)
            script_tags = soup.find_all('script')
            if len(script_tags) > 10:
                indicators.append(f"{len(script_tags)} script tags")
            
            # Check for empty content areas that should have products
            main_content = soup.find('main') or soup.find(id='main') or soup.find(class_=re.compile('main|content'))
            if main_content:
                text_content = main_content.get_text(strip=True)
                if len(text_content) < 500:  # Very little text content
                    indicators.append("minimal text content in main area")
            
            # Check for common "enable JavaScript" messages
            page_text = soup.get_text().lower()
            js_messages = ['enable javascript', 'requires javascript', 'javascript disabled']
            for message in js_messages:
                if message in page_text:
                    indicators.append(f"'{message}' message")
            
            return indicators
            
        except Exception as e:
            self.logger.debug(f"Failed to detect JavaScript requirements: {e}")
            return []

    def _try_text_based_product_extraction(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Try to extract product information from text content when CSS selectors fail.
        
        Args:
            soup: BeautifulSoup parsed page
            
        Returns:
            List of product dictionaries extracted from text
        """
        products = []
        
        try:
            self.logger.debug("Attempting text-based product extraction")
            
            # Look for any text that contains price patterns
            price_pattern = re.compile(r'€(\d+[.,]\d+)')
            page_text = soup.get_text()
            price_matches = price_pattern.findall(page_text)
            
            if price_matches:
                self.logger.debug(f"Found {len(price_matches)} price patterns in text")
                
                # Create placeholder products based on price count
                for i, price_str in enumerate(price_matches[:10]):  # Limit to 10 to avoid spam
                    try:
                        price = float(price_str.replace(',', '.'))
                        products.append({
                            "id": f"text_extracted_prod_{i + 1}",
                            "name": f"Product {i + 1}",
                            "description": f"Product extracted from page text - €{price}",
                            "price": price,
                            "original_price": price,
                            "currency": "EUR",
                            "discount_percentage": 0.0,
                            "offer_name": "",  # No offer extraction in text-based fallback
                            "category": "Extracted",
                            "image_url": "",
                            "availability": True,
                            "options": []
                        })
                        
                    except ValueError:
                        continue
                        
        except Exception as e:
            self.logger.debug(f"Text-based extraction failed: {e}")
        
        return products

    def _create_category_dict(self, name: str, source: str, display_order: int = 0) -> Dict[str, Any]:
        """
        Create a standardized category dictionary.
        
        Args:
            name: Category name
            source: Source of the category (e.g., "heading", "fallback")
            display_order: Display order
            
        Returns:
            Category dictionary
        """
        return {
            "id": self._generate_category_id(name),
            "name": name,
            "description": f"{name} items and products",
            "product_count": 0,  # Will be updated during product linking
            "source": source,
            "display_order": display_order
        }
    
    def _generate_category_id(self, name: str) -> str:
        """
        Generate a unique category ID from the name.
        
        Args:
            name: Category name
            
        Returns:
            Unique category ID
        """
        # Convert to lowercase, replace spaces with underscores, remove special chars
        clean_name = re.sub(r'[^\w\s-]', '', name.lower())
        clean_name = re.sub(r'\s+', '_', clean_name)
        return f"cat_{clean_name}"

    def _extract_offer_name_wolt(self, product_container) -> str:
        """
        Extract offer name from Wolt product container.
        
        Args:
            product_container: BeautifulSoup element containing the product
            
        Returns:
            Offer name or empty string if no offer found
        """
        try:
            # Look for offer span within the product container
            offer_span = product_container.find('span', class_='byr4db3')
            if offer_span:
                offer_text = offer_span.get_text(strip=True)
                # Validate: not empty, reasonable length
                if offer_text and 3 <= len(offer_text) <= 200:
                    return offer_text
            
            return ""
            
        except Exception:
            return ""
