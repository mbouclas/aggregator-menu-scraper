#!/usr/bin/env python3
"""
Test script to inspect the actual DOM structure of the Coffee Island page
to understand how categories are organized.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.scrapers.fast_foody_playwright_scraper import FastFoodyPlaywrightScraper
from src.common.config_manager import ConfigManager

def main():
    config_manager = ConfigManager()
    config = config_manager.get_config('foody.com.cy')
    scraper = FastFoodyPlaywrightScraper(config, 'https://www.foody.com.cy/delivery/menu/coffee-island')
    
    try:
        scraper._setup_browser()
        scraper._navigate_to_page()
        
        print('Page title:', scraper.page.title())
        print('Page loaded successfully')
        
        # Look for actual category structure
        headers = scraper.page.query_selector_all('h2, h3')
        print(f'\nFound {len(headers)} headers:')
        for i, header in enumerate(headers[:20]):
            text = header.text_content().strip()
            if text:
                print(f'{i+1:2d}. "{text}"')
        
        # Look for menu structure
        print(f'\nLooking for menu structure...')
        menu_sections = scraper.page.query_selector_all('.menu-section, .product-section, .category-section')
        print(f'Found {len(menu_sections)} menu sections')
        
        # Look for the actual product container structure
        products = scraper.page.query_selector_all('h3.cc-name_acd53e')
        print(f'\nFound {len(products)} products')
        if products:
            print('First few products:')
            for i, product in enumerate(products[:5]):
                name = product.text_content().strip()
                print(f'{i+1}. "{name}"')
        
    finally:
        scraper._cleanup()

if __name__ == "__main__":
    main()
