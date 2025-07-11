"""
Test cases for the BaseScraper class and JSON output format.
"""
import os
import sys
import unittest
import json
import tempfile
from datetime import datetime

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from common.config import ScraperConfig
from scrapers.example_scraper import ExampleScraper


class TestBaseScraper(unittest.TestCase):
    """Test cases for BaseScraper functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ScraperConfig(
            domain="test.com",
            base_url="https://test.com",
            scraping_method="requests",
            item_selector=".item",
            title_selector=".title",
            price_selector=".price"
        )
        self.target_url = "https://test.com/menu"
        self.scraper = ExampleScraper(self.config, self.target_url)
    
    def test_scraper_initialization(self):
        """Test scraper initialization."""
        self.assertEqual(self.scraper.config.domain, "test.com")
        self.assertEqual(self.scraper.target_url, self.target_url)
        self.assertIsNone(self.scraper.scraped_at)
        self.assertIsNone(self.scraper.processed_at)
    
    def test_scrape_method(self):
        """Test the main scrape method."""
        result = self.scraper.scrape()
        
        # Check main structure
        required_keys = ['metadata', 'source', 'restaurant', 'categories', 'products', 'summary', 'errors']
        for key in required_keys:
            self.assertIn(key, result)
        
        # Check timestamps are set
        self.assertIsNotNone(self.scraper.scraped_at)
        self.assertIsNotNone(self.scraper.processed_at)
        
        # Check metadata
        metadata = result['metadata']
        self.assertEqual(metadata['domain'], 'test.com')
        self.assertEqual(metadata['scraping_method'], 'requests')
        self.assertIsInstance(metadata['processing_duration_seconds'], float)
    
    def test_restaurant_extraction(self):
        """Test restaurant information extraction."""
        restaurant_info = self.scraper.extract_restaurant_info()
        
        required_fields = ['name', 'brand', 'address', 'phone', 'rating', 'delivery_fee', 'minimum_order', 'delivery_time', 'cuisine_types']
        for field in required_fields:
            self.assertIn(field, restaurant_info)
        
        self.assertIsInstance(restaurant_info['rating'], (int, float))
        self.assertIsInstance(restaurant_info['delivery_fee'], (int, float))
        self.assertIsInstance(restaurant_info['cuisine_types'], list)
    
    def test_categories_extraction(self):
        """Test categories extraction."""
        categories = self.scraper.extract_categories()
        
        self.assertIsInstance(categories, list)
        
        if categories:
            category = categories[0]
            required_fields = ['id', 'name', 'description', 'product_count']
            for field in required_fields:
                self.assertIn(field, category)
            
            self.assertIsInstance(category['product_count'], int)
    
    def test_products_extraction(self):
        """Test products extraction."""
        products = self.scraper.extract_products()
        
        self.assertIsInstance(products, list)
        
        if products:
            product = products[0]
            required_fields = ['id', 'name', 'description', 'price', 'original_price', 'currency', 'discount_percentage', 'category', 'image_url', 'availability', 'options']
            for field in required_fields:
                self.assertIn(field, product)
            
            self.assertIsInstance(product['price'], (int, float))
            self.assertIsInstance(product['original_price'], (int, float))
            self.assertIsInstance(product['discount_percentage'], (int, float))
            self.assertIsInstance(product['availability'], bool)
            self.assertIsInstance(product['options'], list)
    
    def test_json_output_structure(self):
        """Test the complete JSON output structure."""
        result = self.scraper.scrape()
        
        # Test that result can be serialized to JSON
        json_str = json.dumps(result)
        self.assertIsInstance(json_str, str)
        
        # Test that JSON can be parsed back
        parsed = json.loads(json_str)
        self.assertEqual(result, parsed)
        
        # Test summary calculations
        summary = result['summary']
        self.assertEqual(summary['total_products'], len(result['products']))
        self.assertEqual(summary['total_categories'], len(result['categories']))
        self.assertIn('price_range', summary)
        
        # Test price range calculations
        price_range = summary['price_range']
        if result['products']:
            prices = [p['price'] for p in result['products'] if p['price'] is not None]
            if prices:
                self.assertEqual(price_range['min'], min(prices))
                self.assertEqual(price_range['max'], max(prices))
    
    def test_error_handling(self):
        """Test error handling functionality."""
        # Add an error
        self.scraper._add_error("test_error", "This is a test error", {"context": "test"})
        
        errors = self.scraper.get_errors()
        self.assertEqual(len(errors), 1)
        
        error = errors[0]
        self.assertEqual(error['type'], 'test_error')
        self.assertEqual(error['message'], 'This is a test error')
        self.assertIn('timestamp', error)
        self.assertIn('context', error)
        
        self.assertTrue(self.scraper.has_errors())
    
    def test_save_output(self):
        """Test saving output to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run scrape first
            self.scraper.scrape()
            
            # Save output
            output_file = self.scraper.save_output(output_dir=temp_dir)
            
            # Check file exists
            self.assertTrue(os.path.exists(output_file))
            
            # Check file contains valid JSON
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Verify structure
            self.assertIn('metadata', data)
            self.assertIn('products', data)
            self.assertIn('categories', data)
    
    def test_summary_generation(self):
        """Test scraper summary generation."""
        # Run scrape first
        self.scraper.scrape()
        
        summary = self.scraper.get_summary()
        
        required_fields = ['domain', 'url', 'scraped_at', 'processed_at', 'products_found', 'categories_found', 'errors_encountered', 'success']
        for field in required_fields:
            self.assertIn(field, summary)
        
        self.assertEqual(summary['domain'], 'test.com')
        self.assertEqual(summary['url'], self.target_url)
        self.assertIsInstance(summary['success'], bool)


if __name__ == '__main__':
    unittest.main()
