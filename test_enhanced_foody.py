#!/usr/bin/env python3
"""
Test script for enhanced foody scraper with product extraction.
"""

from src.scrapers.foody_scraper import FoodyScraper
from src.common.config import ScraperConfig
import json

def main():
    try:
        print("Starting foody scraper test...")
        
        # Load configuration
        config = ScraperConfig.from_markdown_file('scrapers/foody.md')
        print(f'Configuration loaded for domain: {config.domain}')

        # Create scraper and test
        url = 'https://www.foody.com.cy/delivery/menu/costa-coffee'
        scraper = FoodyScraper(config, url)

        print(f'Testing enhanced product extraction with URL: {url}')
        result = scraper.scrape()

        # Display results
        print(f'\n=== SCRAPING RESULTS ===')
        print(f'Available keys: {list(result.keys())}')
        
        if 'restaurant' in result:
            print(f'Restaurant: {result["restaurant"].get("name", "Unknown")}')
            print(f'Restaurant data: {result["restaurant"]}')
        else:
            print('Restaurant info not available')
            
        if 'products' in result:
            print(f'Products found: {len(result["products"])}')
        else:
            print('Products data not available')
            
        if 'categories' in result:
            print(f'Categories found: {len(result["categories"])}')
        else:
            print('Categories data not available')

        # Show first 3 products if any
        if result.get('products'):
            print(f'\n=== FIRST 3 PRODUCTS ===')
            for i, product in enumerate(result['products'][:3]):
                print(f'{i+1}. {product.get("name", "Unknown")} - €{product.get("price", 0)} ({product.get("category", "Unknown")})')

        # Show errors if any
        if result.get('errors'):
            print(f'\n=== ERRORS ({len(result["errors"])}) ===')
            for error in result['errors']:
                print(f'- {error["type"]}: {error["message"]}')

        # Show JSON output structure (just the first 800 chars to see the content)
        json_output = json.dumps(result, indent=2)
        print(f'\n=== JSON OUTPUT ===')
        print(f'Size: {len(json_output)} bytes')
        print('First 800 characters of JSON:')
        print(json_output[:800])
        print('...')
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        import traceback
        print(f"Error occurred: {e}")
        print("Traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
