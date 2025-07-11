"""
Foody.com.cy scraper implementation.

This scraper extracts restaurant and menu data from foody.com.cy
using either requests+BeautifulSoup or Selenium based on configuration.
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional, Tuple
import re
import time
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

from .base_scraper import BaseScraper

# Import Selenium utilities for JavaScript-heavy content
try:
    from ..common.selenium_utils import SeleniumDriver, get_env_selenium_config
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class FoodyScraper(BaseScraper):
    """
    Scraper implementation for foody.com.cy
    
    Supports both requests+BeautifulSoup and Selenium scraping methods
    based on configuration. Automatically detects JavaScript requirements
    and switches to Selenium when needed.
    """
    
    def __init__(self, config, target_url: str):
        """Initialize the Foody scraper."""
        super().__init__(config, target_url)
        
        # Determine scraping method from config
        self.scraping_method = getattr(config, 'scraping_method', 'requests').lower()
        self.requires_javascript = getattr(config, 'requires_javascript', False)
        
        # Initialize appropriate scraper
        if self.scraping_method == 'selenium' or self.requires_javascript:
            self._init_selenium()
        else:
            self._init_requests()
    
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
    
    def _init_selenium(self):
        """Initialize Selenium-based scraping."""
        if not SELENIUM_AVAILABLE:
            self.logger.error("Selenium not available but required by configuration")
            raise ImportError("Selenium required but not installed. Run: pip install selenium webdriver-manager")
        
        # Get Selenium configuration
        self.selenium_config = get_env_selenium_config()
        self.selenium_driver = None
        
        self.logger.info(f"Initialized Selenium scraper (headless: {self.selenium_config['headless']})")
        
    def _fetch_page(self) -> BeautifulSoup:
        """
        Fetch and parse the target page using the configured method.
        
        Returns:
            BeautifulSoup object of the parsed page
            
        Raises:
            Exception: If page cannot be fetched after retries
        """
        if self.scraping_method == 'selenium' or self.requires_javascript:
            return self._fetch_page_selenium()
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
    
    def _fetch_page_selenium(self) -> BeautifulSoup:
        """
        Fetch page using Selenium WebDriver.
        
        Returns:
            BeautifulSoup object of the parsed page
        """
        self.logger.info(f"Fetching page with Selenium: {self.target_url}")
        
        try:
            # Create Selenium driver
            driver = SeleniumDriver(
                headless=self.selenium_config['headless'],
                implicit_wait=self.selenium_config['implicit_wait'],
                page_load_timeout=self.selenium_config['page_load_timeout']
            )
            
            with driver as selenium:
                # Load page and wait for content
                soup = selenium.get_page(self.target_url, wait_for_content=True, max_wait=30)
                
                # Scroll to load any lazy content
                selenium.scroll_to_load_content()
                
                # Get final page state
                final_soup = BeautifulSoup(selenium.driver.page_source, 'html.parser')
                
                self.logger.debug(f"Selenium page loaded, content length: {len(str(final_soup))}")
                return final_soup
                
        except Exception as e:
            self.logger.error(f"Selenium page fetch failed: {e}")
            self._add_error("selenium_fetch_failed", f"Failed to fetch page with Selenium: {str(e)}")
            
            # Fallback to requests if Selenium fails
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
            
            # Extract restaurant name using the configured selector
            restaurant_name = self._extract_restaurant_name(soup)
            if restaurant_name:
                restaurant_info["name"] = restaurant_name
                restaurant_info["brand"] = restaurant_name  # Use same as name for now
                self.logger.debug(f"Extracted restaurant name: {restaurant_name}")
            else:
                self._add_error("restaurant_name_missing", "Could not extract restaurant name")
            
            # Try to extract additional info (these may not be available without JavaScript)
            self._extract_additional_restaurant_info(soup, restaurant_info)
            
            return restaurant_info
            
        except Exception as e:
            self.logger.error(f"Failed to extract restaurant info: {e}")
            self._add_error("restaurant_extraction_failed", str(e))
            return restaurant_info
    
    def _extract_restaurant_name(self, soup: BeautifulSoup) -> str:
        """
        Extract restaurant name using various selector strategies.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Restaurant name or empty string if not found
        """
        # Strategy 1: Look for h1 with class containing "title" (from config)
        h1_selectors = [
            'h1[class*="cc-title"]',
            'h1[class*="title"]',
            'h1.cc-title_58e9e8',  # Specific selector from config
        ]
        
        for selector in h1_selectors:
            try:
                element = soup.select_one(selector)
                if element and element.get_text(strip=True):
                    name = element.get_text(strip=True)
                    self.logger.debug(f"Found restaurant name with selector '{selector}': {name}")
                    return name
            except Exception as e:
                self.logger.debug(f"Selector '{selector}' failed: {e}")
        
        # Strategy 2: Look for any h1 that might contain restaurant name
        h1_elements = soup.find_all('h1')
        for h1 in h1_elements:
            text = h1.get_text(strip=True)
            if text and len(text) > 3:  # Basic validation
                self.logger.debug(f"Found potential restaurant name in h1: {text}")
                return text
        
        # Strategy 3: Look in page title
        title_element = soup.find('title')
        if title_element:
            title_text = title_element.get_text(strip=True)
            # Extract restaurant name from title (usually format: "Restaurant Name - Foody")
            if ' - ' in title_text:
                restaurant_name = title_text.split(' - ')[0].strip()
                if restaurant_name and restaurant_name.lower() != 'foody':
                    self.logger.debug(f"Extracted restaurant name from title: {restaurant_name}")
                    return restaurant_name
        
        # Strategy 4: Look for meta tags
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            content = og_title['content'].strip()
            if content and len(content) > 3:
                self.logger.debug(f"Found restaurant name in og:title: {content}")
                return content
        
        self.logger.warning("Could not extract restaurant name using any strategy")
        return ""
    
    def _extract_additional_restaurant_info(self, soup: BeautifulSoup, restaurant_info: Dict[str, Any]):
        """
        Try to extract additional restaurant information from the page.
        
        Args:
            soup: BeautifulSoup object
            restaurant_info: Dictionary to update with extracted info
        """
        # Note: Many of these fields may require JavaScript execution
        # This is a basic attempt that may not find much data
        
        # Try to find rating
        rating_selectors = [
            '[class*="rating"]',
            '[class*="score"]',
            '.rating-value',
            '[data-rating]'
        ]
        
        for selector in rating_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    rating_text = element.get_text(strip=True)
                    # Extract numeric rating
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        rating = float(rating_match.group(1))
                        if 0 <= rating <= 5:  # Validate rating range
                            restaurant_info["rating"] = rating
                            self.logger.debug(f"Extracted rating: {rating}")
                            break
            except Exception as e:
                self.logger.debug(f"Rating extraction failed with selector '{selector}': {e}")
        
        # Try to find delivery info
        delivery_selectors = [
            '[class*="delivery"]',
            '[class*="fee"]',
            '.delivery-info'
        ]
        
        for selector in delivery_selectors:
            try:
                elements = soup.select(selector)
                for element in elements[:3]:  # Check first few matches
                    text = element.get_text(strip=True)
                    
                    # Look for delivery fee
                    fee_match = re.search(r'(\d+\.?\d*)\s*€', text)
                    if fee_match and restaurant_info["delivery_fee"] == 0.0:
                        restaurant_info["delivery_fee"] = float(fee_match.group(1))
                        self.logger.debug(f"Extracted delivery fee: {restaurant_info['delivery_fee']}€")
                    
                    # Look for minimum order
                    if 'minimum' in text.lower() or 'min' in text.lower():
                        min_match = re.search(r'(\d+\.?\d*)\s*€', text)
                        if min_match and restaurant_info["minimum_order"] == 0.0:
                            restaurant_info["minimum_order"] = float(min_match.group(1))
                            self.logger.debug(f"Extracted minimum order: {restaurant_info['minimum_order']}€")
                    
                    # Look for delivery time
                    time_match = re.search(r'(\d+[-–]\d+|\d+)\s*(min|minutes)', text, re.IGNORECASE)
                    if time_match and not restaurant_info["delivery_time"]:
                        restaurant_info["delivery_time"] = time_match.group(0)
                        self.logger.debug(f"Extracted delivery time: {restaurant_info['delivery_time']}")
                        
            except Exception as e:
                self.logger.debug(f"Delivery info extraction failed: {e}")
    
    def extract_categories(self) -> List[Dict[str, Any]]:
        """
        Extract product categories from foody.com.cy using comprehensive detection.
        
        Returns:
            List of category dictionaries with proper structure
        """
        self.logger.info("Extracting categories using foody.com.cy specific methods")
        
        try:
            soup = self._fetch_page()
            categories = []
            
            # Check if page requires JavaScript (affects category availability)
            js_indicators = self._detect_javascript_requirements(soup)
            if js_indicators:
                # Only warn if we're not using Selenium (which handles JavaScript)
                if self.scraping_method != 'selenium':
                    self.logger.warning(f"Page requires JavaScript for dynamic content: {js_indicators}")
                    self._add_error("javascript_required_categories", 
                                  f"Category extraction limited due to JavaScript requirements: {', '.join(js_indicators)}")
                else:
                    # With Selenium, just log as debug since we're handling JavaScript
                    self.logger.debug(f"JavaScript detected (handled by Selenium): {js_indicators}")
                    # Still record as info for transparency but don't treat as error
                    self._add_error("javascript_detected_selenium", 
                                  f"JavaScript content detected (handled by Selenium): {', '.join(js_indicators)}")
            
            # Strategy 1: Look for h2 elements (menu sections/categories)
            categories_found = self._extract_categories_from_headings(soup)
            categories.extend(categories_found)
            
            # Strategy 2: Look for navigation menu categories
            nav_categories = self._extract_categories_from_navigation(soup)
            categories.extend(nav_categories)
            
            # Strategy 3: Extract from product structure (reverse engineering)
            structural_categories = self._extract_categories_from_structure(soup)
            categories.extend(structural_categories)
            
            # Strategy 4: Fallback - create categories from common foody.com.cy patterns
            if not categories and js_indicators:
                fallback_categories = self._create_fallback_categories()
                categories.extend(fallback_categories)
                self.logger.info("Using fallback categories due to JavaScript requirements")
            
            # Remove duplicates and clean up
            unique_categories = self._deduplicate_categories(categories)
            
            # Ensure we have at least some basic categories for foody.com.cy
            if not unique_categories:
                unique_categories = self._ensure_minimum_categories()
            
            self.logger.info(f"Extracted {len(unique_categories)} categories")
            return unique_categories
            
        except Exception as e:
            self.logger.error(f"Failed to extract categories: {e}")
            self._add_error("category_extraction_failed", str(e))
            return self._ensure_minimum_categories()
    
    def _extract_categories_from_headings(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract categories from h2, h3 heading elements."""
        categories = []
        
        try:
            # Look for heading elements that might be categories
            heading_selectors = [
                'h2',  # Main category headers
                'h3[class*="category"]',  # Category-specific h3s
                'h2[class*="menu"]',  # Menu section headers
                '[class*="category-title"]',  # Category title classes
                '[class*="section-title"]',  # Section title classes
            ]
            
            for selector in heading_selectors:
                elements = soup.select(selector)
                self.logger.debug(f"Found {len(elements)} elements with selector '{selector}'")
                
                for element in elements:
                    category_text = element.get_text(strip=True)
                    if self._is_valid_category_text(category_text):
                        cleaned_name = self._clean_category_name(category_text)
                        if cleaned_name:
                            categories.append(self._create_category_dict(cleaned_name, "heading"))
                            
                            if len(categories) >= 10:  # Reasonable limit
                                break
                
                if len(categories) >= 10:
                    break
                    
        except Exception as e:
            self.logger.debug(f"Heading category extraction failed: {e}")
        
        return categories
    
    def _extract_categories_from_navigation(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract categories from navigation menus or category filters."""
        categories = []
        
        try:
            # Look for navigation elements
            nav_selectors = [
                'nav a',  # Navigation links
                '.menu-nav a',  # Menu navigation
                '[class*="category-filter"]',  # Category filters
                '[class*="category-nav"]',  # Category navigation
                '.filter-option',  # Filter options
                '[role="tab"]',  # Tab-based category selection
            ]
            
            for selector in nav_selectors:
                elements = soup.select(selector)
                self.logger.debug(f"Found {len(elements)} navigation elements with '{selector}'")
                
                for element in elements:
                    category_text = element.get_text(strip=True)
                    if self._is_valid_category_text(category_text):
                        cleaned_name = self._clean_category_name(category_text)
                        if cleaned_name:
                            categories.append(self._create_category_dict(cleaned_name, "navigation"))
                            
                            if len(categories) >= 8:  # Limit nav categories
                                break
                
                if len(categories) >= 8:
                    break
                    
        except Exception as e:
            self.logger.debug(f"Navigation category extraction failed: {e}")
        
        return categories
    
    def _extract_categories_from_structure(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract categories by analyzing the page structure."""
        categories = []
        
        try:
            # Look for structural elements that might indicate categories
            structure_selectors = [
                '[class*="menu-section"]',  # Menu sections
                '[class*="product-group"]',  # Product groups
                '[data-category]',  # Elements with category data attributes
                '.section',  # Generic sections
                '[class*="cc-section"]',  # Costa Coffee sections
            ]
            
            for selector in structure_selectors:
                elements = soup.select(selector)
                self.logger.debug(f"Found {len(elements)} structural elements with '{selector}'")
                
                for element in elements:
                    # Look for category indicators in this element
                    category_indicators = element.select('h2, h3, [class*="title"]')
                    
                    for indicator in category_indicators:
                        category_text = indicator.get_text(strip=True)
                        if self._is_valid_category_text(category_text):
                            cleaned_name = self._clean_category_name(category_text)
                            if cleaned_name:
                                categories.append(self._create_category_dict(cleaned_name, "structure"))
                                
                                if len(categories) >= 6:
                                    break
                
                if len(categories) >= 6:
                    break
                    
        except Exception as e:
            self.logger.debug(f"Structural category extraction failed: {e}")
        
        return categories
    
    def _create_fallback_categories(self) -> List[Dict[str, Any]]:
        """Create fallback categories typical for foody.com.cy restaurants."""
        fallback_names = [
            "Hot Drinks",
            "Cold Drinks", 
            "Coffee",
            "Tea",
            "Food",
            "Snacks",
            "Desserts",
            "Specials"
        ]
        
        categories = []
        for name in fallback_names:
            categories.append(self._create_category_dict(name, "fallback"))
        
        return categories
    
    def _is_valid_category_text(self, text: str) -> bool:
        """Check if text is likely to be a valid category name."""
        if not text or len(text) < 2 or len(text) > 60:
            return False
        
        # Skip common non-category texts
        skip_patterns = [
            r'^\d+$',  # Pure numbers
            r'^(home|about|contact|login|register)$',  # Common page names
            r'^(click|tap|see|view|show|hide)$',  # Action words
            r'^(and|or|with|from|to|of|in|on|at)$',  # Prepositions
            r'(loading|spinner|skeleton)',  # Loading indicators
        ]
        
        text_lower = text.lower()
        for pattern in skip_patterns:
            if re.match(pattern, text_lower):
                return False
        
        # Prefer texts that look like category names
        category_keywords = [
            'drink', 'coffee', 'tea', 'food', 'snack', 'dessert', 'special',
            'hot', 'cold', 'fresh', 'organic', 'menu', 'offer', 'deal'
        ]
        
        # If it contains category keywords, it's probably valid
        for keyword in category_keywords:
            if keyword in text_lower:
                return True
        
        # Otherwise, accept if it looks like a reasonable category name
        # (capitalized, not too many special characters)
        if re.match(r'^[A-Z][a-zA-Z\s&-]+$', text):
            return True
        
        return False
    
    def _clean_category_name(self, text: str) -> str:
        """Clean and normalize category name."""
        if not text:
            return ""
        
        # Remove numbers and extra whitespace
        cleaned = re.sub(r'\d+', '', text).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove common prefixes/suffixes
        cleaned = re.sub(r'^(category|section|menu):\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*(menu|section|category)$', '', cleaned, flags=re.IGNORECASE)
        
        # Capitalize properly
        if cleaned and len(cleaned) > 1:
            # Split on spaces and capitalize each word
            words = cleaned.split()
            capitalized_words = []
            for word in words:
                if len(word) > 2:
                    capitalized_words.append(word.capitalize())
                else:
                    capitalized_words.append(word.upper())  # For short words like "& "
            cleaned = ' '.join(capitalized_words)
        
        return cleaned.strip()
    
    def _create_category_dict(self, name: str, source: str) -> Dict[str, Any]:
        """Create a category dictionary with standard structure."""
        category_id = f"cat_{name.lower().replace(' ', '_').replace('&', 'and')}"
        
        return {
            "id": category_id,
            "name": name,
            "description": f"{name} items and products",
            "product_count": 0,  # Will be updated when linking with products
            "source": source,  # Track where this category came from for debugging
            "display_order": 0  # Can be used for ordering categories
        }
    
    def _deduplicate_categories(self, categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate categories based on name similarity."""
        if not categories:
            return []
        
        unique_categories = []
        seen_names = set()
        
        for category in categories:
            name_lower = category['name'].lower().strip()
            
            # Check for exact duplicates
            if name_lower in seen_names:
                continue
            
            # Check for similar names (e.g., "Coffee" vs "Coffees")
            is_similar = False
            for seen_name in seen_names:
                if (name_lower in seen_name or seen_name in name_lower) and \
                   abs(len(name_lower) - len(seen_name)) <= 2:
                    is_similar = True
                    break
            
            if not is_similar:
                seen_names.add(name_lower)
                category['display_order'] = len(unique_categories)
                unique_categories.append(category)
        
        return unique_categories
    
    def _ensure_minimum_categories(self) -> List[Dict[str, Any]]:
        """Ensure we have at least basic categories for any restaurant."""
        basic_categories = [
            "Beverages",
            "Food",
            "Specials"
        ]
        
        categories = []
        for i, name in enumerate(basic_categories):
            categories.append({
                "id": f"cat_basic_{i+1}",
                "name": name,
                "description": f"Basic {name.lower()} category",
                "product_count": 0,
                "source": "minimum_required",
                "display_order": i
            })
        
        return categories
    
    def extract_products(self) -> List[Dict[str, Any]]:
        """
        Extract product information using foody.com.cy specific selectors.
        
        Returns:
            List of product dictionaries
        """
        self.logger.info("Extracting products using foody.com.cy selectors")
        
        try:
            soup = self._fetch_page()
            products = []
            
            # Check if page requires JavaScript (common indicators)
            js_indicators = self._detect_javascript_requirements(soup)
            if js_indicators:
                # Only warn if we're not using Selenium (which handles JavaScript)
                if self.scraping_method != 'selenium':
                    self.logger.warning(f"Page appears to require JavaScript: {js_indicators}")
                    self._add_error("javascript_required", 
                                  f"Page requires JavaScript for dynamic content loading. Found indicators: {', '.join(js_indicators)}")
                else:
                    # With Selenium, just log as debug since we're handling JavaScript
                    self.logger.debug(f"JavaScript detected (handled by Selenium): {js_indicators}")
                    # Record as info but not an error since Selenium handles it
                    self._add_error("javascript_detected_selenium", 
                                  f"JavaScript content detected (handled by Selenium): {', '.join(js_indicators)}")
            
            # Use specific selectors from foody.md configuration
            product_title_selectors = [
                'h3.cc-name_acd53e',  # Primary selector from config
                'h3[class*="cc-name"]',  # Variation of the class
                'h3[class*="name"]',  # Fallback
                '.product-name h3',  # Alternative structure
                '[class*="cc-name"]',  # Any element with cc-name class
                '[class*="menu-item"]',  # Menu item containers
                '[class*="product"]',  # Product containers
            ]
            
            self.logger.debug("Searching for products with foody.com.cy selectors")
            
            for selector in product_title_selectors:
                try:
                    title_elements = soup.select(selector)
                    self.logger.debug(f"Found {len(title_elements)} elements with selector '{selector}'")
                    
                    if title_elements:
                        # Process each product title element
                        for i, title_element in enumerate(title_elements):
                            try:
                                product_data = self._extract_single_product(title_element, i + 1)
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
            
            if not products:
                error_msg = "Could not find products using any configured selector"
                if js_indicators:
                    if self.scraping_method == 'selenium':
                        error_msg += ". Page uses JavaScript for dynamic content (Selenium is handling this, but selectors may need adjustment)"
                    else:
                        error_msg += ". Page requires JavaScript for dynamic content - consider using Selenium instead of requests+BeautifulSoup"
                
                self.logger.warning(error_msg)
                self._add_error("no_products_found", error_msg, {"javascript_required": bool(js_indicators)})
            
            return products
            
        except Exception as e:
            self.logger.error(f"Failed to extract products: {e}")
            self._add_error("product_extraction_failed", str(e))
            return []
    
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
            price_pattern = re.compile(r'(\d+[.,]\d+)\s*€')
            page_text = soup.get_text()
            price_matches = price_pattern.findall(page_text)
            
            if price_matches:
                self.logger.debug(f"Found {len(price_matches)} price patterns in text")
                
                # Create placeholder products based on price count
                for i, price_str in enumerate(price_matches[:5]):  # Limit to 5 to avoid spam
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
                            "category": "Text Extracted",
                            "image_url": "",
                            "availability": True,
                            "options": []
                        })
                    except ValueError:
                        continue
                
                if products:
                    self.logger.info(f"Extracted {len(products)} products using text-based method")
                    self._add_error("text_based_extraction", 
                                  f"Used fallback text extraction due to JavaScript requirements. Found {len(products)} price patterns.")
            
            return products
            
        except Exception as e:
            self.logger.debug(f"Text-based extraction failed: {e}")
            return []
    
    def _extract_single_product(self, title_element, product_index: int) -> Dict[str, Any]:
        """
        Extract a single product's information from its title element.
        
        Args:
            title_element: BeautifulSoup element containing the product title
            product_index: Index for generating unique product ID
            
        Returns:
            Product dictionary or None if extraction fails
        """
        try:
            # Extract product name
            product_name = title_element.get_text(strip=True)
            if not product_name or len(product_name) < 2:
                return None
            
            # Find the product container (usually a parent div)
            product_container = self._find_product_container(title_element)
            
            # Extract price using foody-specific price selectors
            price, original_price = self._extract_product_price(product_container or title_element)
            
            # Extract category (from nearest h2 parent)
            category = self._extract_product_category(title_element)
            
            # Extract description (if available)
            description = self._extract_product_description(product_container or title_element)
            
            # Build product data structure
            product_data = {
                "id": f"foody_prod_{product_index}",
                "name": product_name,
                "description": description or f"Product: {product_name}",
                "price": price,
                "original_price": original_price,
                "currency": "EUR",
                "discount_percentage": self._calculate_discount_percentage(price, original_price),
                "category": category or "General",
                "image_url": "",  # Will be enhanced later
                "availability": True,  # Assume available if listed
                "options": []  # Will be enhanced later
            }
            
            return product_data
            
        except Exception as e:
            self.logger.debug(f"Single product extraction failed: {e}")
            return None
    
    def _find_product_container(self, title_element):
        """
        Find the container element that holds all product information.
        
        Args:
            title_element: The h3 title element
            
        Returns:
            Container element or None if not found
        """
        # Try to find the product container by traversing up the DOM
        current = title_element
        
        # Look for common container patterns
        for _ in range(5):  # Limit traversal depth
            if current.parent:
                parent = current.parent
                
                # Check if parent looks like a product container
                if any(class_name in str(parent.get('class', [])) for class_name in 
                       ['product', 'item', 'card', 'menu-item']):
                    return parent
                
                # Check if parent has both title and price elements
                if (parent.find('h3') and 
                    (parent.find(class_=re.compile(r'price|cc-price')) or 
                     parent.find(string=re.compile(r'\d+[.,]\d*\s*€')))):
                    return parent
                
                current = parent
            else:
                break
        
        return None
    
    def _extract_product_price(self, container) -> Tuple[float, float]:
        """
        Extract product price using foody.com.cy specific price selectors.
        
        Args:
            container: BeautifulSoup element to search for price
            
        Returns:
            Tuple of (current_price, original_price)
        """
        current_price = 0.0
        original_price = 0.0
        
        try:
            # Primary price selectors from foody.md config
            price_selectors = [
                '.cc-price_a7d252',  # Primary selector from config
                '[class*="cc-price"]',  # Variations
                '[class*="price"]',  # General price classes
                '.price',  # Fallback
            ]
            
            for selector in price_selectors:
                price_elements = container.select(selector)
                
                for price_element in price_elements:
                    price_text = price_element.get_text(strip=True)
                    parsed_price = self._parse_price_text(price_text)
                    
                    if parsed_price > 0:
                        current_price = parsed_price
                        original_price = parsed_price  # Will be updated if discount found
                        self.logger.debug(f"Found price: €{parsed_price} with selector '{selector}'")
                        break
                
                if current_price > 0:
                    break
            
            # If no price found with selectors, try regex search in container text
            if current_price == 0.0:
                container_text = container.get_text() if container else ""
                parsed_price = self._parse_price_from_text(container_text)
                if parsed_price > 0:
                    current_price = parsed_price
                    original_price = parsed_price
                    self.logger.debug(f"Found price in text: €{parsed_price}")
            
            return current_price, original_price
            
        except Exception as e:
            self.logger.debug(f"Price extraction failed: {e}")
            return 0.0, 0.0
    
    def _parse_price_text(self, price_text: str) -> float:
        """
        Parse price text according to foody.com.cy format.
        
        Args:
            price_text: Raw price text from HTML
            
        Returns:
            Parsed price as float, or 0.0 if parsing fails
        """
        if not price_text:
            return 0.0
        
        try:
            # Remove "From" prefix as specified in config
            cleaned_text = re.sub(r'^\s*From\s+', '', price_text, flags=re.IGNORECASE)
            
            # Extract price with € symbol
            # Matches patterns like: "19.45€", "20.90 €", "15,50€"
            price_match = re.search(r'(\d+[.,]\d+|\d+)\s*€', cleaned_text)
            
            if price_match:
                price_str = price_match.group(1)
                # Replace comma with dot for float conversion
                price_str = price_str.replace(',', '.')
                price = float(price_str)
                return price
            
            return 0.0
            
        except (ValueError, AttributeError) as e:
            self.logger.debug(f"Price parsing failed for '{price_text}': {e}")
            return 0.0
    
    def _parse_price_from_text(self, text: str) -> float:
        """
        Extract price from general text using regex.
        
        Args:
            text: Text to search for price patterns
            
        Returns:
            Parsed price or 0.0 if not found
        """
        if not text:
            return 0.0
        
        # Look for price patterns in text
        price_patterns = [
            r'(?:From\s+)?(\d+[.,]\d+)\s*€',  # "From 19.45€" or "19.45€"
            r'€\s*(\d+[.,]\d+)',  # "€19.45"
            r'(\d+[.,]\d+)\s*EUR',  # "19.45 EUR"
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    price_str = match.group(1).replace(',', '.')
                    return float(price_str)
                except ValueError:
                    continue
        
        return 0.0
    
    def _extract_product_category(self, title_element) -> str:
        """
        Extract product category by finding the nearest h2 parent element.
        
        Args:
            title_element: Product title element
            
        Returns:
            Category name or empty string
        """
        try:
            # According to config: "Categories are always the first h2 parent of each product"
            current = title_element
            
            # Traverse up the DOM to find an h2 element
            for _ in range(10):  # Limit search depth
                if current.parent:
                    # Look for h2 siblings or ancestors
                    h2_elements = current.parent.find_all('h2')
                    
                    if h2_elements:
                        # Get the first h2 that appears before this product
                        for h2 in h2_elements:
                            category_text = h2.get_text(strip=True)
                            if category_text and len(category_text) < 50:  # Reasonable category length
                                # Clean category name as specified in config
                                cleaned_category = re.sub(r'\d+', '', category_text).strip()
                                cleaned_category = re.sub(r'\s+', ' ', cleaned_category)
                                if cleaned_category:
                                    return cleaned_category
                    
                    current = current.parent
                else:
                    break
            
            # Fallback: look for any h2 in the page that might be a category
            soup = title_element.find_parent('html') or title_element.find_parent()
            if soup:
                h2_elements = soup.find_all('h2')
                for h2 in h2_elements:
                    category_text = h2.get_text(strip=True)
                    # Check if this looks like a menu category
                    if any(keyword in category_text.lower() for keyword in 
                           ['coffee', 'drink', 'food', 'dessert', 'offer', 'special']):
                        cleaned_category = re.sub(r'\d+', '', category_text).strip()
                        cleaned_category = re.sub(r'\s+', ' ', cleaned_category)
                        return cleaned_category
            
            return ""
            
        except Exception as e:
            self.logger.debug(f"Category extraction failed: {e}")
            return ""
    
    def _extract_product_description(self, container) -> str:
        """
        Extract product description if available.
        
        Args:
            container: Product container element
            
        Returns:
            Description text or empty string
        """
        try:
            if not container:
                return ""
            
            # Look for common description selectors
            description_selectors = [
                '.description',
                '.product-description', 
                'p',
                '.details',
                '[class*="desc"]'
            ]
            
            for selector in description_selectors:
                desc_element = container.select_one(selector)
                if desc_element:
                    desc_text = desc_element.get_text(strip=True)
                    # Validate description (not too short, not the title)
                    if desc_text and len(desc_text) > 10 and len(desc_text) < 500:
                        return desc_text
            
            return ""
            
        except Exception as e:
            self.logger.debug(f"Description extraction failed: {e}")
            return ""
    
    def _calculate_discount_percentage(self, current_price: float, original_price: float) -> float:
        """
        Calculate discount percentage.
        
        Args:
            current_price: Current price
            original_price: Original price before discount
            
        Returns:
            Discount percentage (0.0 if no discount)
        """
        try:
            if original_price > current_price > 0:
                discount = ((original_price - current_price) / original_price) * 100
                return round(discount, 2)
            return 0.0
        except (ZeroDivisionError, TypeError):
            return 0.0
    
    def scrape(self) -> Dict[str, Any]:
        """
        Override base scrape method to properly link categories and products.
        
        Returns:
            Complete scraped data with linked categories and products
        """
        self.logger.info(f"Starting enhanced foody.com.cy scrape of {self.target_url}")
        self.scraped_at = datetime.now(timezone.utc)
        
        try:
            # Extract data using the enhanced methods
            self._restaurant_info = self.extract_restaurant_info()
            self._categories = self.extract_categories()
            self._products = self.extract_products()
            
            # Link products to categories and update counts
            self._link_products_and_categories()
            
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
    
    def _link_products_and_categories(self):
        """
        Link products to categories and update category product counts.
        Ensures all product categories exist in the categories array.
        """
        if not self._categories or not self._products:
            self.logger.debug("No categories or products to link")
            return
        
        # Create category lookup
        category_map = {cat['name'].lower(): cat for cat in self._categories}
        category_counts = {cat['id']: 0 for cat in self._categories}
        
        # Process each product
        unmatched_categories = set()
        
        for product in self._products:
            product_category = product.get('category', '').strip()
            
            if not product_category:
                # Assign to a default category
                product['category'] = 'General'
                product_category = 'General'
            
            # Find matching category (case-insensitive)
            category_key = product_category.lower()
            matched_category = None
            
            # Exact match first
            if category_key in category_map:
                matched_category = category_map[category_key]
            else:
                # Partial match (e.g., "Hot Coffee" matches "Coffee")
                for cat_name, cat_obj in category_map.items():
                    if category_key in cat_name or cat_name in category_key:
                        matched_category = cat_obj
                        product['category'] = cat_obj['name']  # Standardize the name
                        break
            
            if matched_category:
                # Update count for matched category
                category_counts[matched_category['id']] += 1
            else:
                # Track unmatched categories
                unmatched_categories.add(product_category)
        
        # Add any missing categories that products reference
        for unmatched_category in unmatched_categories:
            if unmatched_category and unmatched_category != 'General':
                new_category = self._create_category_dict(unmatched_category, "product_derived")
                new_category['id'] = f"cat_derived_{len(self._categories) + 1}"
                self._categories.append(new_category)
                category_counts[new_category['id']] = 0
                
                # Update count for this new category
                for product in self._products:
                    if product.get('category', '').lower() == unmatched_category.lower():
                        category_counts[new_category['id']] += 1
                        product['category'] = new_category['name']  # Standardize
        
        # Ensure "General" category exists if any products use it
        general_needed = any(p.get('category') == 'General' for p in self._products)
        if general_needed and not any(cat['name'] == 'General' for cat in self._categories):
            general_category = self._create_category_dict('General', "auto_created")
            general_category['id'] = "cat_general"
            self._categories.append(general_category)
            category_counts[general_category['id']] = 0
        
        # Update all category product counts
        for category in self._categories:
            category['product_count'] = category_counts.get(category['id'], 0)
        
        # Remove categories with zero products (unless they're fallback categories)
        self._categories = [
            cat for cat in self._categories 
            if cat['product_count'] > 0 or cat.get('source') in ['fallback', 'minimum_required', 'auto_created']
        ]
        
        self.logger.info(f"Linked {len(self._products)} products across {len(self._categories)} categories")
        
        # Debug logging
        for category in self._categories:
            self.logger.debug(f"Category '{category['name']}': {category['product_count']} products")

    # ...existing code...
