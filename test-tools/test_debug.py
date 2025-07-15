#!/usr/bin/env python3
"""
Debug test script with logging.
"""

import logging
import sys
import os
sys.path.append('src')

# Set logging to DEBUG level
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')

from src.scrapers.fast_foody_playwright_scraper import FastFoodyPlaywrightScraper

def test_with_debug():
    """Test scraper with debug logging."""
    print('Testing with debug logging...')

    try:
        # Create a simple config mock
        class MockConfig:
            domain = 'foody.com.cy'
            requires_javascript = True
            
        config = MockConfig()
        scraper = FastFoodyPlaywrightScraper(config, 'https://www.foody.com.cy/delivery/menu/the-big-bad-wolf')
        
        # Test just the first few products
        result = scraper.extract_products()
        print(f'Found {len(result)} products')
        
        # Check for offers
        offers_found = [p for p in result if p.get('offer_name')]
        print(f'Products with offers: {len(offers_found)}')
        for p in offers_found[:5]:
            print(f"  {p['name']}: '{p['offer_name']}'")
            
        # Also check if any products have the names we expect
        target_names = ["1+1 Giant Greek Pita", "Greek Pita for €4.00", "Say Beef Burger Menu €8"]
        for target in target_names:
            found = [p for p in result if target in p['name']]
            if found:
                p = found[0]
                print(f"Target product '{target}': offer_name = '{p['offer_name']}'")
            else:
                print(f"Target product '{target}': NOT FOUND")
                
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_debug()
