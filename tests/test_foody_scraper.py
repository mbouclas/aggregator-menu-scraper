"""
Test cases for the FoodyScraper implementation.
"""
import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
import json

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

try:
    from common.config import ScraperConfig
    from scrapers.foody_scraper import FoodyScraper
    # Import will work if dependencies are available
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Some dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False


@unittest.skipUnless(DEPENDENCIES_AVAILABLE, "Required dependencies not available")
class TestFoodyScraper(unittest.TestCase):
    """Test cases for FoodyScraper functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ScraperConfig(
            domain="foody.com.cy",
            base_url="https://www.foody.com.cy",
            scraping_method="requests",
            restaurant_name_selector="h1[class*='cc-title']",
            title_selector="h3[class*='cc-name']",
            price_selector="[class*='price']"
        )
        self.target_url = "https://www.foody.com.cy/delivery/menu/costa-coffee"
        self.scraper = FoodyScraper(self.config, self.target_url)
    
    def test_scraper_initialization(self):
        """Test scraper initialization."""
        self.assertEqual(self.scraper.config.domain, "foody.com.cy")
        self.assertEqual(self.scraper.target_url, self.target_url)
        self.assertIsNotNone(self.scraper.session)
        self.assertIn('User-Agent', self.scraper.session.headers)
    
    @patch('scrapers.foody_scraper.requests.Session.get')
    def test_fetch_page_success(self, mock_get):
        """Test successful page fetching."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html><head><title>Test</title></head><body><h1>Test Restaurant</h1></body></html>'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        soup = self.scraper._fetch_page()
        
        self.assertIsNotNone(soup)
        self.assertEqual(soup.find('title').get_text(), 'Test')
        mock_get.assert_called_once_with(self.target_url, timeout=30)
    
    @patch('scrapers.foody_scraper.requests.Session.get')
    def test_fetch_page_retry_on_failure(self, mock_get):
        """Test retry mechanism on page fetch failure."""
        import requests
        
        # Mock first two calls to fail, third to succeed
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html><body><h1>Success</h1></body></html>'
        mock_response.raise_for_status.return_value = None
        
        mock_get.side_effect = [
            requests.exceptions.RequestException("Network error"),
            requests.exceptions.RequestException("Network error"),
            mock_response
        ]
        
        # Patch time.sleep to avoid actual delays
        with patch('scrapers.foody_scraper.time.sleep'):
            soup = self.scraper._fetch_page()
        
        self.assertIsNotNone(soup)
        self.assertEqual(mock_get.call_count, 3)
    
    @patch('scrapers.foody_scraper.FoodyScraper._fetch_page')
    def test_extract_restaurant_name_from_h1(self, mock_fetch):
        """Test restaurant name extraction from h1 element."""
        from bs4 import BeautifulSoup
        
        html_content = '''
        <html>
            <body>
                <h1 class="cc-title_58e9e8">Costa Coffee Stavrou</h1>
                <div>Other content</div>
            </body>
        </html>
        '''
        
        mock_fetch.return_value = BeautifulSoup(html_content, 'html.parser')
        
        restaurant_info = self.scraper.extract_restaurant_info()
        
        self.assertEqual(restaurant_info['name'], 'Costa Coffee Stavrou')
        self.assertEqual(restaurant_info['brand'], 'Costa Coffee Stavrou')
        self.assertFalse(self.scraper.has_errors())
    
    @patch('scrapers.foody_scraper.FoodyScraper._fetch_page')
    def test_extract_restaurant_name_from_title(self, mock_fetch):
        """Test restaurant name extraction from page title when h1 not found."""
        from bs4 import BeautifulSoup
        
        html_content = '''
        <html>
            <head>
                <title>KFC Nikis - Foody</title>
            </head>
            <body>
                <div>Some content without h1</div>
            </body>
        </html>
        '''
        
        mock_fetch.return_value = BeautifulSoup(html_content, 'html.parser')
        
        restaurant_info = self.scraper.extract_restaurant_info()
        
        self.assertEqual(restaurant_info['name'], 'KFC Nikis')
        self.assertEqual(restaurant_info['brand'], 'KFC Nikis')
    
    @patch('scrapers.foody_scraper.FoodyScraper._fetch_page')
    def test_extract_categories(self, mock_fetch):
        """Test category extraction."""
        from bs4 import BeautifulSoup
        
        html_content = '''
        <html>
            <body>
                <h2 class="category-header">Offers</h2>
                <h2>Cold Coffees</h2>
                <h2>Hot Drinks</h2>
                <h2>123 Desserts</h2>
            </body>
        </html>
        '''
        
        mock_fetch.return_value = BeautifulSoup(html_content, 'html.parser')
        
        categories = self.scraper.extract_categories()
        
        self.assertGreater(len(categories), 0)
        
        # Check that categories were found and cleaned
        category_names = [cat['name'] for cat in categories]
        
        # Should include cleaned categories (numbers removed)
        self.assertIn('Offers', category_names)
        self.assertIn('Cold Coffees', category_names)
        
        # Check structure
        if categories:
            category = categories[0]
            required_fields = ['id', 'name', 'description', 'product_count']
            for field in required_fields:
                self.assertIn(field, category)
    
    @patch('scrapers.foody_scraper.FoodyScraper._fetch_page')
    def test_extract_products(self, mock_fetch):
        """Test product extraction."""
        from bs4 import BeautifulSoup
        
        html_content = '''
        <html>
            <body>
                <div class="product">
                    <h3 class="cc-name_acd53e">Freddo Espresso Massimo</h3>
                    <div class="cc-price_a7d252">4.50€</div>
                </div>
                <div class="product">
                    <h3 class="cc-name_acd53e">Cold Brew with Milk</h3>
                    <div class="price">From 5.20€</div>
                </div>
            </body>
        </html>
        '''
        
        mock_fetch.return_value = BeautifulSoup(html_content, 'html.parser')
        
        products = self.scraper.extract_products()
        
        self.assertGreater(len(products), 0)
        
        # Check structure
        if products:
            product = products[0]
            required_fields = ['id', 'name', 'description', 'price', 'original_price', 'currency', 'discount_percentage', 'category', 'image_url', 'availability', 'options']
            for field in required_fields:
                self.assertIn(field, product)
            
            # Check that product names were extracted
            product_names = [prod['name'] for prod in products]
            self.assertIn('Freddo Espresso Massimo', product_names)
    
    @patch('scrapers.foody_scraper.FoodyScraper._fetch_page')
    def test_price_extraction(self, mock_fetch):
        """Test price extraction functionality."""
        from bs4 import BeautifulSoup
        
        html_content = '''
        <div class="product">
            <h3>Test Product</h3>
            <span>19.45€</span>
        </div>
        '''
        
        soup = BeautifulSoup(html_content, 'html.parser')
        h3_element = soup.find('h3')
        
        price = self.scraper._extract_price_near_element(h3_element)
        self.assertEqual(price, 19.45)
    
    @patch('scrapers.foody_scraper.FoodyScraper._fetch_page')
    def test_complete_scrape_workflow(self, mock_fetch):
        """Test the complete scraping workflow."""
        from bs4 import BeautifulSoup
        
        html_content = '''
        <html>
            <head>
                <title>Costa Coffee - Foody</title>
            </head>
            <body>
                <h1 class="cc-title_58e9e8">Costa Coffee Stavrou</h1>
                <h2>Cold Coffees</h2>
                <h2>Hot Drinks</h2>
                <div class="menu">
                    <h3 class="cc-name_acd53e">Freddo Espresso</h3>
                    <span>4.50€</span>
                    <h3 class="cc-name_acd53e">Cappuccino</h3>
                    <span>3.80€</span>
                </div>
            </body>
        </html>
        '''
        
        mock_fetch.return_value = BeautifulSoup(html_content, 'html.parser')
        
        # Run the complete scrape
        result = self.scraper.scrape()
        
        # Validate JSON structure
        required_keys = ['metadata', 'source', 'restaurant', 'categories', 'products', 'summary', 'errors']
        for key in required_keys:
            self.assertIn(key, result)
        
        # Check that restaurant name was extracted
        self.assertEqual(result['restaurant']['name'], 'Costa Coffee Stavrou')
        
        # Check that some categories were found
        self.assertGreater(len(result['categories']), 0)
        
        # Check that some products were found
        self.assertGreater(len(result['products']), 0)
        
        # Validate JSON serializability
        json_str = json.dumps(result)
        self.assertIsInstance(json_str, str)
    
    def test_url_validation(self):
        """Test that scraper validates foody.com.cy URLs correctly."""
        valid_urls = [
            "https://www.foody.com.cy/delivery/menu/costa-coffee",
            "https://www.foody.com.cy/delivery/menu/kfc-nikis"
        ]
        
        invalid_urls = [
            "https://www.other-site.com/menu",
            "https://foody.com/menu",  # Wrong domain
            "https://www.foody.com.gr/menu"  # Wrong TLD
        ]
        
        for url in valid_urls:
            self.assertTrue(self.config.matches_url(url), f"Should match: {url}")
        
        for url in invalid_urls:
            self.assertFalse(self.config.matches_url(url), f"Should not match: {url}")


class TestFoodyScraperBasic(unittest.TestCase):
    """Basic tests that don't require external dependencies."""
    
    def test_import_structure(self):
        """Test that the scraper can be imported properly."""
        try:
            from scrapers.foody_scraper import FoodyScraper
            self.assertTrue(True, "FoodyScraper can be imported")
        except ImportError as e:
            self.skipTest(f"Cannot import FoodyScraper: {e}")


if __name__ == '__main__':
    unittest.main()
