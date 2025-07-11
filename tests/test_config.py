"""
Test cases for the configuration loading system.
"""
import os
import sys
import unittest
from unittest.mock import patch, mock_open

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from common.config import ScraperConfig
from common.factory import ScraperFactory


class TestScraperConfig(unittest.TestCase):
    """Test cases for ScraperConfig class."""
    
    def test_simple_config_parsing(self):
        """Test parsing of simple template format."""
        markdown_content = """
### base_url
`https://example.com`

### item_selector
```css
.product-card
```

### title_selector
`h3.product-title`

### price_selector
`.price`
"""
        
        config = ScraperConfig(domain="example.com")
        config._parse_markdown_content(markdown_content)
        
        self.assertEqual(config.base_url, "https://example.com")
        self.assertEqual(config.item_selector, ".product-card")
        self.assertEqual(config.title_selector, "h3.product-title")
        self.assertEqual(config.price_selector, ".price")
    
    def test_detailed_config_parsing(self):
        """Test parsing of detailed foody format."""
        markdown_content = """
# Foody.com.cy Scraper Configuration

## Scraping Strategy
- **Method**: Selenium (JavaScript heavy site)
- **JavaScript Required**: Yes
- **Anti-bot Protection**: Basic rate limiting
- **URL Pattern**: `^https://www\.foody\.com\.cy/delivery/menu/.*`

## Testing URLs
- Primary: https://www.foody.com.cy/delivery/menu/costa-coffee
- Secondary: https://www.foody.com.cy/delivery/menu/pasta-strada
"""
        
        config = ScraperConfig(domain="foody.com.cy")
        config._parse_markdown_content(markdown_content)
        
        self.assertEqual(config.scraping_method, "selenium")
        self.assertTrue(config.requires_javascript)
        self.assertEqual(config.anti_bot_protection, "Basic rate limiting")
        self.assertEqual(config.url_pattern, "^https://www\.foody\.com\.cy/delivery/menu/.*")
        self.assertEqual(len(config.testing_urls), 2)
    
    def test_url_matching(self):
        """Test URL matching functionality."""
        config = ScraperConfig(
            domain="foody.com.cy",
            url_pattern=r"^https://www\.foody\.com\.cy/delivery/menu/.*"
        )
        
        # Should match
        self.assertTrue(config.matches_url("https://www.foody.com.cy/delivery/menu/costa-coffee"))
        
        # Should not match (different path)
        self.assertFalse(config.matches_url("https://www.foody.com.cy/restaurants"))
        
        # Should not match (different domain)
        self.assertFalse(config.matches_url("https://www.other-site.com/delivery/menu/test"))


class TestScraperFactory(unittest.TestCase):
    """Test cases for ScraperFactory class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_dir = "/test/configs"
    
    @patch('glob.glob')
    @patch('os.path.exists')
    def test_factory_initialization(self, mock_exists, mock_glob):
        """Test factory initialization."""
        mock_exists.return_value = True
        mock_glob.return_value = []
        
        factory = ScraperFactory(self.test_config_dir)
        self.assertEqual(factory.config_directory, self.test_config_dir)
        self.assertEqual(len(factory.configs), 0)
    
    def test_url_config_matching(self):
        """Test getting configuration for URL."""
        factory = ScraperFactory(self.test_config_dir)
        
        # Add a test configuration
        test_config = ScraperConfig(
            domain="foody.com.cy",
            url_pattern=r"^https://www\.foody\.com\.cy/delivery/menu/.*"
        )
        factory.add_config(test_config)
        
        # Test URL matching
        config = factory.get_config_for_url("https://www.foody.com.cy/delivery/menu/costa-coffee")
        self.assertIsNotNone(config)
        self.assertEqual(config.domain, "foody.com.cy")
        
        # Test no match
        config = factory.get_config_for_url("https://www.unknown-site.com/menu")
        self.assertIsNone(config)


if __name__ == '__main__':
    unittest.main()
