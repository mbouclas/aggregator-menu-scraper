"""
Demo script to test the FoodyScraper implementation.

This script demonstrates how to use the FoodyScraper with the
foody.com.cy configuration to extract basic restaurant information.
"""
import os
import sys
import json

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

# Check if required dependencies are available
try:
    import requests
    import bs4
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Required dependencies not available: {e}")
    print("Please install dependencies with: pip install requests beautifulsoup4 lxml")
    DEPENDENCIES_AVAILABLE = False

from common import ScraperFactory, setup_logging, get_logger

if DEPENDENCIES_AVAILABLE:
    from scrapers.foody_scraper import FoodyScraper


def test_with_dependencies():
    """Test the FoodyScraper with actual dependencies."""
    print("=== FoodyScraper Demo with Real Dependencies ===\n")
    
    # Set up logging
    setup_logging(log_level="INFO")
    logger = get_logger(__name__)
    
    # Load the foody.com.cy configuration
    factory = ScraperFactory()
    config = factory.get_config_for_url("https://www.foody.com.cy/delivery/menu/costa-coffee")
    
    if not config:
        print("❌ No configuration found for foody.com.cy")
        return
    
    print(f"✅ Using configuration for: {config.domain}")
    print(f"   Scraping method: {config.scraping_method}")
    print(f"   Restaurant selector: {config.restaurant_name_selector}")
    print(f"   Product selector: {config.title_selector}")
    
    # Create the scraper
    target_url = "https://www.foody.com.cy/delivery/menu/costa-coffee"
    scraper = FoodyScraper(config, target_url)
    
    print(f"\n🚀 Testing FoodyScraper with URL: {target_url}")
    print("   Note: This will make an actual HTTP request to foody.com.cy")
    
    # Test just the URL validation first
    print(f"\n🔍 URL Validation:")
    print(f"   URL matches config pattern: {config.matches_url(target_url)}")
    
    try:
        # Test individual extraction methods
        print(f"\n📊 Testing Restaurant Info Extraction:")
        restaurant_info = scraper.extract_restaurant_info()
        
        print(f"   Restaurant Name: {restaurant_info.get('name', 'Not found')}")
        print(f"   Brand: {restaurant_info.get('brand', 'Not found')}")
        print(f"   Rating: {restaurant_info.get('rating', 'Not found')}")
        print(f"   Delivery Fee: €{restaurant_info.get('delivery_fee', 'Not found')}")
        
        if restaurant_info.get('name'):
            print("   ✅ Restaurant name extraction successful")
        else:
            print("   ⚠️  Restaurant name not found (may require JavaScript)")
        
        # Test categories
        print(f"\n📂 Testing Category Extraction:")
        categories = scraper.extract_categories()
        print(f"   Found {len(categories)} categories")
        
        for i, category in enumerate(categories[:3]):  # Show first 3
            print(f"   {i+1}. {category['name']}")
        
        # Test products
        print(f"\n🍕 Testing Product Extraction:")
        products = scraper.extract_products()
        print(f"   Found {len(products)} products")
        
        for i, product in enumerate(products[:3]):  # Show first 3
            print(f"   {i+1}. {product['name']} - €{product['price']}")
        
        # Run complete scrape
        print(f"\n🔄 Running Complete Scrape:")
        result = scraper.scrape()
        
        # Show results
        print(f"   Total Products: {result['summary']['total_products']}")
        print(f"   Total Categories: {result['summary']['total_categories']}")
        print(f"   Errors: {len(result['errors'])}")
        
        if result['errors']:
            print(f"   Error Types: {[e['type'] for e in result['errors']]}")
        
        # Show processing info
        metadata = result['metadata']
        print(f"   Processing Duration: {metadata['processing_duration_seconds']:.2f}s")
        print(f"   Scraped At: {metadata['scraped_at']}")
        
        # Save output
        print(f"\n💾 Saving Output:")
        output_file = scraper.save_output()
        print(f"   Saved to: {output_file}")
        
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"   File size: {file_size:,} bytes")
            
            # Validate JSON
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    json.load(f)
                print(f"   ✅ JSON is valid")
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON validation failed: {e}")
        
        # Summary
        print(f"\n📋 Summary:")
        success = len(result['errors']) == 0 and result['restaurant']['name']
        print(f"   Success: {success}")
        print(f"   Restaurant Found: {bool(result['restaurant']['name'])}")
        print(f"   Data Extracted: {result['summary']['total_products']} products, {result['summary']['total_categories']} categories")
        
        if not success:
            print(f"\n⚠️  Note: Limited data may be due to JavaScript requirements.")
            print(f"   Consider upgrading to Selenium for full extraction.")
        
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        print(f"   This might be due to network issues, site changes, or JavaScript requirements")


def test_without_dependencies():
    """Test basic functionality without external dependencies."""
    print("=== FoodyScraper Basic Tests (No Dependencies) ===\n")
    
    # Test configuration loading
    factory = ScraperFactory()
    config = factory.get_config_for_url("https://www.foody.com.cy/delivery/menu/costa-coffee")
    
    if config:
        print(f"✅ Configuration loaded for: {config.domain}")
        print(f"   URL Pattern: {config.url_pattern}")
        print(f"   Scraping Method: {config.scraping_method}")
        print(f"   Requires JavaScript: {config.requires_javascript}")
    else:
        print("❌ Failed to load foody.com.cy configuration")
    
    # Test URL matching
    test_urls = [
        "https://www.foody.com.cy/delivery/menu/costa-coffee",
        "https://www.foody.com.cy/delivery/menu/kfc-nikis",
        "https://www.other-site.com/menu"
    ]
    
    print(f"\n🔍 URL Matching Tests:")
    for url in test_urls:
        if config:
            matches = config.matches_url(url)
            status = "✅" if matches else "❌"
            print(f"   {status} {url}")
        else:
            print(f"   ❓ {url} (no config to test)")
    
    # Test basic class structure
    print(f"\n🏗️  Class Structure:")
    try:
        from scrapers.foody_scraper import FoodyScraper
        print(f"   ✅ FoodyScraper class can be imported")
        
        # Check methods exist
        methods = ['extract_restaurant_info', 'extract_categories', 'extract_products']
        for method in methods:
            if hasattr(FoodyScraper, method):
                print(f"   ✅ Method {method} exists")
            else:
                print(f"   ❌ Method {method} missing")
                
    except ImportError as e:
        print(f"   ❌ Cannot import FoodyScraper: {e}")


def main():
    """Main demo function."""
    print("🍕 Foody.com.cy Scraper Demo\n")
    
    if DEPENDENCIES_AVAILABLE:
        test_with_dependencies()
    else:
        print("Running basic tests without external dependencies...\n")
        test_without_dependencies()
        print(f"\n💡 To test with actual scraping, install dependencies:")
        print(f"   pip install requests beautifulsoup4 lxml")


if __name__ == "__main__":
    main()
