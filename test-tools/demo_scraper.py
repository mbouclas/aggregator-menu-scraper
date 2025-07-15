"""
Demo script to test the BaseScraper class and JSON output format.

This script demonstrates:
1. How to use the BaseScraper with a ScraperConfig
2. The structure of the JSON output
3. Error handling and logging
4. Saving output to files
"""
import os
import sys
import json

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from common import ScraperFactory, setup_logging, get_logger
from scrapers.example_scraper import ExampleScraper


def main():
    """Main demo function."""
    # Set up logging
    setup_logging(log_level="INFO")
    logger = get_logger(__name__)
    
    print("=== BaseScraper Demo ===\n")
    
    # 1. Load a configuration
    factory = ScraperFactory()
    config = factory.get_config_for_url("https://www.foody.com.cy/delivery/menu/costa-coffee")
    
    if not config:
        print("❌ No configuration found for the test URL")
        return
    
    print(f"✅ Using configuration for: {config.domain}")
    print(f"   Scraping method: {config.scraping_method}")
    print(f"   Requires JavaScript: {config.requires_javascript}")
    
    # 2. Create and run scraper
    target_url = "https://www.foody.com.cy/delivery/menu/costa-coffee"
    scraper = ExampleScraper(config, target_url)
    
    print(f"\n🚀 Starting scrape of: {target_url}")
    
    # Perform the scrape
    result = scraper.scrape()
    
    # 3. Display results
    print(f"\n📊 Scraping Results:")
    print(f"   Restaurant: {result['restaurant']['name']}")
    print(f"   Categories: {len(result['categories'])} found")
    print(f"   Products: {len(result['products'])} found")
    print(f"   Errors: {len(result['errors'])} encountered")
    
    # 4. Show summary
    summary = result['summary']
    print(f"\n📈 Summary:")
    print(f"   Price range: €{summary['price_range']['min']} - €{summary['price_range']['max']}")
    print(f"   Average price: €{summary['price_range']['average']}")
    print(f"   Available products: {summary['available_products']}/{summary['total_products']}")
    print(f"   Products with discounts: {summary['products_with_discounts']}")
    
    # 5. Show metadata
    metadata = result['metadata']
    print(f"\n🔍 Metadata:")
    print(f"   Processing duration: {metadata['processing_duration_seconds']:.2f} seconds")
    print(f"   Scraped at: {metadata['scraped_at']}")
    print(f"   Scraper version: {metadata['scraper_version']}")
    
    # 6. Display sample data
    print(f"\n📝 Sample Data:")
    
    # Show first category
    if result['categories']:
        cat = result['categories'][0]
        print(f"   First Category: {cat['name']} ({cat['product_count']} products)")
    
    # Show first product
    if result['products']:
        prod = result['products'][0]
        print(f"   First Product: {prod['name']} - €{prod['price']}")
        if prod['discount_percentage'] > 0:
            print(f"     Discount: {prod['discount_percentage']:.1f}% off (was €{prod['original_price']})")
    
    # 7. Save to file
    print(f"\n💾 Saving output...")
    output_file = scraper.save_output()
    print(f"   Saved to: {output_file}")
    
    # 8. Show file size and validation
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
    
    # 9. Show configuration details used
    print(f"\n⚙️  Configuration Details:")
    print(f"   Domain: {config.domain}")
    print(f"   Base URL: {config.base_url}")
    print(f"   Title selector: {config.title_selector}")
    print(f"   Price selector: {config.price_selector}")
    
    # 10. Show scraper summary
    scraper_summary = scraper.get_summary()
    print(f"\n📋 Scraper Summary:")
    print(f"   Success: {scraper_summary['success']}")
    print(f"   Products found: {scraper_summary['products_found']}")
    print(f"   Categories found: {scraper_summary['categories_found']}")
    print(f"   Errors: {scraper_summary['errors_encountered']}")


def show_json_structure():
    """Show the expected JSON output structure."""
    print("\n=== Expected JSON Output Structure ===")
    
    structure = {
        "metadata": {
            "scraper_version": "string",
            "domain": "string", 
            "scraping_method": "string",
            "scraped_at": "ISO datetime",
            "processed_at": "ISO datetime",
            "processing_duration_seconds": "float",
            "error_count": "int",
            "product_count": "int",
            "category_count": "int"
        },
        "source": {
            "url": "string",
            "domain": "string",
            "scraped_at": "ISO datetime"
        },
        "restaurant": {
            "name": "string",
            "brand": "string", 
            "address": "string",
            "phone": "string",
            "rating": "float",
            "delivery_fee": "float",
            "minimum_order": "float",
            "delivery_time": "string",
            "cuisine_types": ["string"]
        },
        "categories": [
            {
                "id": "string",
                "name": "string",
                "description": "string",
                "product_count": "int"
            }
        ],
        "products": [
            {
                "id": "string",
                "name": "string",
                "description": "string",
                "price": "float",
                "original_price": "float",
                "currency": "string",
                "discount_percentage": "float",
                "category": "string",
                "image_url": "string",
                "availability": "boolean",
                "options": [{"name": "string", "choices": ["string"]}]
            }
        ],
        "summary": {
            "total_products": "int",
            "total_categories": "int",
            "price_range": {
                "min": "float",
                "max": "float", 
                "average": "float",
                "currency": "string"
            },
            "available_products": "int",
            "products_with_discounts": "int"
        },
        "errors": [
            {
                "type": "string",
                "message": "string",
                "timestamp": "ISO datetime",
                "context": "object"
            }
        ]
    }
    
    print(json.dumps(structure, indent=2))


if __name__ == "__main__":
    main()
    show_json_structure()
