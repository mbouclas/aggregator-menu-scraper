#!/usr/bin/env python3
"""
Debug script to investigate offer structure on foody.com.cy pages.
This script will help us understand why offer names aren't being extracted.
"""

import sys
import os
import time
sys.path.append('src')

from bs4 import BeautifulSoup
from src.common.fast_playwright_utils import FastPlaywrightManager, fast_page_fetch, fast_get_text_content, fast_find_elements

def debug_offer_structure():
    """Debug the HTML structure around offers on the foody page."""
    
    target_url = "https://www.foody.com.cy/delivery/menu/the-big-bad-wolf"
    
    try:
        # Setup Playwright
        print("🔧 Setting up Playwright...")
        playwright_manager = FastPlaywrightManager(
            headless=True,
            timeout=15000,
            disable_images=True,
            disable_css=False  # Keep CSS to see structure better
        )
        
        page = playwright_manager.create_fast_driver()
        print("✅ Playwright ready")
        
        # Load the page
        print(f"📄 Loading page: {target_url}")
        content = fast_page_fetch(page, target_url, wait_time=3)
        print("✅ Page loaded")
        
        # Look for offer-related elements
        print("\n🔍 Searching for offer elements...")
        
        # Search for spans with sn-title class
        offer_selectors = [
            'span.sn-title_522dc0',
            '[class*="sn-title"]',
            '.sn-title',
            '[class*="badge"]',
            '.cc-badge',
            'span[class*="deal"]',
            'span[class*="offer"]'
        ]
        
        for selector in offer_selectors:
            try:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"\n✅ Found {len(elements)} elements with selector: {selector}")
                    for i, element in enumerate(elements[:5]):  # Show first 5
                        try:
                            text = element.text_content().strip()
                            outer_html = element.evaluate("el => el.outerHTML")
                            parent_html = element.evaluate("el => el.parentElement ? el.parentElement.outerHTML.substring(0, 200) + '...' : 'No parent'")
                            
                            print(f"   Element {i+1}:")
                            print(f"     Text: '{text}'")
                            print(f"     HTML: {outer_html}")
                            print(f"     Parent: {parent_html}")
                            print()
                        except Exception as e:
                            print(f"     Error getting element {i+1}: {e}")
                else:
                    print(f"❌ No elements found with selector: {selector}")
            except Exception as e:
                print(f"❌ Error with selector {selector}: {e}")
        
        # Now let's look for the specific product names and see if there are offers nearby
        print("\n🔍 Looking for products and nearby offers...")
        product_elements = page.query_selector_all('h3.cc-name_acd53e')
        
        if product_elements:
            print(f"✅ Found {len(product_elements)} products")
            
            # Check the first few products for offers
            for i, product in enumerate(product_elements[:10]):
                try:
                    product_name = product.text_content().strip()
                    print(f"\n   Product {i+1}: '{product_name}'")
                    
                    # Look for offers in the product's container and siblings
                    container = product.evaluate("el => el.closest('.menu-item, .product-item, .cc-product, .product-container, div')")
                    if container:
                        # Look for offer elements within the container
                        for selector in ['span.sn-title_522dc0', '[class*="sn-title"]', '.sn-title']:
                            offer_element = container.query_selector(selector)
                            if offer_element:
                                offer_text = offer_element.text_content().strip()
                                print(f"     ✅ Found offer: '{offer_text}' (selector: {selector})")
                                
                                # Show the container structure
                                container_html = container.evaluate("el => el.outerHTML.substring(0, 300) + '...'")
                                print(f"     Container: {container_html}")
                                break
                        else:
                            print(f"     ❌ No offers found in container")
                    else:
                        print(f"     ❌ No container found")
                        
                except Exception as e:
                    print(f"     Error checking product {i+1}: {e}")
        else:
            print("❌ No products found")
        
        # Search more broadly for text containing the offers mentioned by user
        print("\n🔍 Searching for specific offer texts...")
        specific_offers = ["1+1 Deals", "Foody deals", "8€ meals"]
        
        for offer_text in specific_offers:
            try:
                # Use XPath to find any element containing this text
                xpath = f"//*[contains(text(), '{offer_text}')]"
                elements = page.locator(xpath).all()
                
                if elements:
                    print(f"✅ Found '{offer_text}' in {len(elements)} elements:")
                    for j, element in enumerate(elements[:3]):
                        try:
                            tag_name = element.evaluate("el => el.tagName")
                            class_name = element.evaluate("el => el.className")
                            outer_html = element.evaluate("el => el.outerHTML")
                            parent_html = element.evaluate("el => el.parentElement ? el.parentElement.outerHTML.substring(0, 200) + '...' : 'No parent'")
                            
                            print(f"   Element {j+1}: <{tag_name} class='{class_name}'>")
                            print(f"     HTML: {outer_html}")
                            print(f"     Parent: {parent_html}")
                            print()
                        except Exception as e:
                            print(f"     Error with element {j+1}: {e}")
                else:
                    print(f"❌ '{offer_text}' not found on page")
                    
            except Exception as e:
                print(f"❌ Error searching for '{offer_text}': {e}")
        
        # Close Playwright
        playwright_manager.close()
        print("\n✅ Debug complete")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 Debugging Foody Offer Structure")
    print("=" * 50)
    debug_offer_structure()
