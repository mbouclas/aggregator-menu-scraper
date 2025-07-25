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
            
            # Fast category extraction using proper Foody structure
            category_selectors = [
                'h2',  # Main category headers as per config
            ]
            
            # First, try to find the Categories list structure
            categories_header = None
            try:
                headers = fast_find_elements(self.page, 'h2')
                for header in headers:
                    text = fast_get_text_content(header).strip()
                    if text.lower() == 'categories':
                        categories_header = header
                        break
            except:
                pass
            
            # If we found the Categories header, extract from the following ul
            if categories_header:
                try:
                    # Look for ul element following the Categories h2
                    ul_element = categories_header.evaluate("""
                        el => {
                            let sibling = el.nextElementSibling;
                            while (sibling && sibling.tagName !== 'UL') {
                                sibling = sibling.nextElementSibling;
                            }
                            return sibling;
                        }
                    """)
                    
                    if ul_element:
                        # Extract li elements from the ul
                        li_elements = fast_find_elements(ul_element, 'li')
                        for i, li in enumerate(li_elements):
                            text = fast_get_text_content(li).strip()
                            if text and len(text) > 2 and len(text) < 50:  # Valid category name
                                # Clean category name as per config
                                cleaned_text = re.sub(r'\d+', '', text).strip()
                                cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
                                if cleaned_text:
                                    category_id = f"cat_{cleaned_text.lower().replace(' ', '_').replace('&', 'and')}"
                                    category = {
                                        "id": category_id,
                                        "name": cleaned_text,
                                        "description": f"{cleaned_text} items and products",
                                        "product_count": 0,
                                        "source": "categories_list",
                                        "display_order": i
                                    }
                                    categories.append(category)
                except Exception as e:
                    self.logger.debug(f"Categories list extraction failed: {e}")
            
            # Fallback: Extract from h2 elements but filter to only real categories
            if not categories:
                try:
                    h2_elements = fast_find_elements(self.page, 'h2')
                    for i, element in enumerate(h2_elements):
                        text = fast_get_text_content(element).strip()
                        if text and self._is_valid_category_name(text):
                            # Clean category name as per config
                            cleaned_text = re.sub(r'\d+', '', text).strip()
                            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
                            if cleaned_text:
                                category_id = f"cat_{cleaned_text.lower().replace(' ', '_').replace('&', 'and')}"
                                category = {
                                    "id": category_id,
                                    "name": cleaned_text,
                                    "description": f"{cleaned_text} items and products",
                                    "product_count": 0,
                                    "source": "h2_headers",
                                    "display_order": i
                                }
                                categories.append(category)
                except Exception as e:
                    self.logger.debug(f"H2 category extraction failed: {e}")
            
            extraction_time = time.time() - start_time
            self.timing_data['content_extraction'] += extraction_time
            
            self.logger.info(f"Extracted {len(categories)} categories in {extraction_time:.2f}s")
            return categories
            
        except Exception as e:
            self.logger.error(f"Error extracting categories: {e}")
            return []
    
    def _is_valid_category_name(self, text: str) -> bool:
        """Check if text is likely to be a valid category name for Foody."""
        if not text or len(text) < 2 or len(text) > 50:
            return False
        
        # Skip common non-category texts
        skip_patterns = [
            r'^\d+$',  # Pure numbers
            r'^(home|about|contact|login|register|account|basket|checkout)$',  # Common page names
            r'^(click|tap|see|view|show|hide|select|add|remove)$',  # Action words
            r'^(and|or|with|from|to|of|in|on|at|the|a|an)$',  # Articles/prepositions
            r'(loading|spinner|skeleton)',  # Loading indicators
            r'^(categories|menu|items|products)$',  # Generic labels
        ]
        
        text_lower = text.lower()
        for pattern in skip_patterns:
            if re.match(pattern, text_lower):
                return False
        
        # For Foody, valid categories typically contain coffee/food related terms
        # Based on config examples: "Offers", "Cold Coffees", "Hot Coffees"
        valid_category_patterns = [
            r'(coffee|drink|tea|beverage)',  # Coffee/drink categories
            r'(food|snack|dessert|sweet)',   # Food categories
            r'(hot|cold|iced|fresh)',        # Temperature descriptors
            r'(offer|special|deal|promo)',   # Promotional categories
            r'^(breakfast|lunch|dinner)',    # Meal types
            r'(espresso|latte|cappuccino|americano)',  # Coffee types
        ]
        
        # If it contains valid category keywords, it's probably a category
        for pattern in valid_category_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # For simple, short names that look like categories (e.g., "Offers")
        if re.match(r'^[A-Z][a-zA-Z\s&-]+$', text) and len(text.split()) <= 3:
            return True
        
        return False

    def _extract_offer_name_fast(self, element) -> str:
        """
        Fast offer name extraction with robust error handling.
        """
        try:
            # Direct approach - use JavaScript to find offer in the same container
            offer_text = element.evaluate("""
                el => {
                    try {
                        // Look in parent container for price wrapper
                        if (el.parentElement) {
                            let priceWrapper = el.parentElement.querySelector('.cc-priceWrapper_8d8617');
                            if (priceWrapper) {
                                let offerSpan = priceWrapper.querySelector('span.sn-title_522dc0');
                                if (offerSpan) {
                                    let text = offerSpan.textContent.trim();
                                    // Validate: not empty, no %, not "up to", reasonable length
                                    if (text && !text.includes('%') && !text.toLowerCase().startsWith('up to') && text.length >= 2 && text.length <= 50) {
                                        return text;
                                    }
                                }
                            }
                            
                            // Fallback: look directly in parent
                            let directOffer = el.parentElement.querySelector('span.sn-title_522dc0');
                            if (directOffer) {
                                let text = directOffer.textContent.trim();
                                if (text && !text.includes('%') && !text.toLowerCase().startsWith('up to') && text.length >= 2 && text.length <= 50) {
                                    return text;
                                }
                            }
                        }
                        return '';
                    } catch (e) {
                        return '';
                    }
                }
            """)
            
            return offer_text or ""
            
        except Exception:
            return ""

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
                            # Fast offer name extraction
                            self.logger.debug(f"Extracting offer for product: '{name}'")
                            offer_name = self._extract_offer_name_fast(element)
                            self.logger.debug(f"Extracted offer name: '{offer_name}' for product: '{name}'")
                            
                            # Fast category extraction for this product
                            category = self._extract_product_category_fast(element)
                            
                            product = {
                                "id": f"foody_prod_{i + 1}",
                                "name": name,
                                "description": f"Product: {name}",
                                "price": 0.0,
                                "original_price": 0.0,
                                "currency": "EUR",
                                "discount_percentage": 0.0,
                                "offer_name": offer_name,  # Add offer name field
                                "category": category or "General",
                                "image_url": "",
                                "availability": True,
                                "options": []
                            }
                            
                            # Fast price extraction with updated Foody selectors
                            try:
                                # First try to find price in the parent container
                                parent = element.evaluate("el => el.closest('.menu-item, .product-item, .cc-product')")
                                if parent:
                                    # Use the correct Foody price selectors from documentation
                                    price_element = parent.query_selector('.cc-price_a7d252, .price, .cc-price, [data-price]')
                                    if price_element:
                                        price_text = fast_get_text_content(price_element)
                                        # Extract price including handling "From" prefix and € symbol
                                        price_match = re.search(r'(?:From\s+)?(\d+\.?\d*)€?', price_text.replace(',', '.'))
                                        if price_match:
                                            product["price"] = float(price_match.group(1))
                                            product["original_price"] = product["price"]
                                
                                # If no price found in parent, try searching in siblings
                                if product["price"] == 0.0:
                                    # Look for price in adjacent elements
                                    price_elements = element.evaluate("""
                                        el => {
                                            const container = el.closest('div, li, section');
                                            if (container) {
                                                const priceSelectors = [
                                                    '.cc-price_a7d252',
                                                    '.price',
                                                    '.cc-price',
                                                    '[data-price]'
                                                ];
                                                for (const selector of priceSelectors) {
                                                    const priceEl = container.querySelector(selector);
                                                    if (priceEl) return priceEl.textContent;
                                                }
                                            }
                                            return null;
                                        }
                                    """)
                                    
                                    if price_elements:
                                        price_match = re.search(r'(?:From\s+)?(\d+\.?\d*)€?', price_elements.replace(',', '.'))
                                        if price_match:
                                            product["price"] = float(price_match.group(1))
                                            product["original_price"] = product["price"]
                            except Exception as e:
                                self.logger.debug(f"Price extraction error for {name}: {e}")
                                pass
                            
                            # Extract discount percentage if present
                            try:
                                discount_info = element.evaluate("""
                                    el => {
                                        const container = el.closest('div, li, section');
                                        if (container) {
                                            // Look for discount badge with percentage
                                            const discountSelectors = [
                                                '.sn-wrapper_6bd59d .sn-title_522dc0',
                                                '.cc-badge_e1275b .sn-title_522dc0',
                                                'span.sn-title_522dc0'
                                            ];
                                            for (const selector of discountSelectors) {
                                                const discountEl = container.querySelector(selector);
                                                if (discountEl) {
                                                    const text = discountEl.textContent;
                                                    const match = text.match(/(?:up to\\s+)?-?(\\d+)%/);
                                                    if (match) {
                                                        return parseInt(match[1]);
                                                    }
                                                }
                                            }
                                        }
                                        return 0;
                                    }
                                """)
                                
                                if discount_info and discount_info > 0:
                                    product["discount_percentage"] = discount_info
                                    self.logger.debug(f"Found discount {discount_info}% for product: '{name}'")
                            except Exception as e:
                                self.logger.debug(f"Discount extraction error for {name}: {e}")
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
    
    def _extract_product_category_fast(self, title_element) -> str:
        """
        Fast product category extraction by finding the first h2 parent element.
        According to Foody config: "Categories are always the first h2 parent of each product"
        
        Args:
            title_element: Product title element
            
        Returns:
            Category name or empty string
        """
        try:
            # Use JavaScript to traverse DOM and find the first h2 parent
            category_text = title_element.evaluate("""
                el => {
                    try {
                        // Traverse up the DOM to find the first h2 parent
                        let current = el;
                        for (let i = 0; i < 10; i++) {
                            if (current.parentElement) {
                                // Look for h2 elements in this parent
                                const h2Elements = current.parentElement.querySelectorAll('h2');
                                if (h2Elements.length > 0) {
                                    // Get the first h2 that appears before this product in document order
                                    for (const h2 of h2Elements) {
                                        const text = h2.textContent.trim();
                                        if (text && text.length < 50 && text.length > 2) {
                                            // Use the first h2 found as per config
                                            return text;
                                        }
                                    }
                                }
                                current = current.parentElement;
                            } else {
                                break;
                            }
                        }
                        
                        // Fallback: find any h2 that comes before this element in the page
                        const allH2s = document.querySelectorAll('h2');
                        const elementPosition = el.getBoundingClientRect().top;
                        
                        let bestH2 = null;
                        let bestDistance = Infinity;
                        
                        for (const h2 of allH2s) {
                            const h2Position = h2.getBoundingClientRect().top;
                            if (h2Position < elementPosition) {
                                const distance = elementPosition - h2Position;
                                if (distance < bestDistance) {
                                    const text = h2.textContent.trim();
                                    if (text && text.length < 50 && text.length > 2) {
                                        bestH2 = text;
                                        bestDistance = distance;
                                    }
                                }
                            }
                        }
                        
                        return bestH2 || '';
                    } catch (e) {
                        return '';
                    }
                }
            """)
            
            if category_text:
                # Clean the category text as per config
                cleaned_category = re.sub(r'\d+', '', category_text).strip()
                cleaned_category = re.sub(r'\s+', ' ', cleaned_category)
                return cleaned_category
            
            return ""
            
        except Exception as e:
            self.logger.debug(f"Fast category extraction failed: {e}")
            return ""

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
