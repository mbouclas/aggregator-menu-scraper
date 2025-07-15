#!/usr/bin/env python3
"""
Advanced debug script to understand DOM relationship between products and offers.
"""

import sys
import os
sys.path.append('src')

from src.common.fast_playwright_utils import FastPlaywrightManager, fast_page_fetch

def debug_product_offer_relationship():
    """Debug the exact DOM relationship between products and offers."""
    
    target_url = "https://www.foody.com.cy/delivery/menu/the-big-bad-wolf"
    
    try:
        playwright_manager = FastPlaywrightManager(headless=True, timeout=15000)
        page = playwright_manager.create_fast_driver()
        
        print("📄 Loading page...")
        fast_page_fetch(page, target_url, wait_time=3)
        
        # Get specific products that we know have offers based on names
        print("\n🔍 Looking for products with offers in their names...")
        
        # Products that should have offers (based on the debug output product names)
        target_products = [
            "1+1 Giant Greek Pita",  # Should have "1+1 Deals"
            "Greek Pita for €4.00",  # Should have "Foody deals"
            "Say Beef Burger Menu €8",  # Should have "8€ meals"
            "Say Chicken Burger Menu €8"  # Should have "8€ meals"
        ]
        
        for product_name in target_products:
            print(f"\n--- Analyzing: '{product_name}' ---")
            
            # Find the product element by its text content
            product_element = page.locator(f"h3.cc-name_acd53e:has-text('{product_name}')").first
            
            if product_element.count() > 0:
                print(f"✅ Found product element")
                
                # Get the full DOM structure around this product
                dom_structure = product_element.evaluate("""
                    el => {
                        let result = {
                            elementHTML: el.outerHTML,
                            parentHTML: el.parentElement ? el.parentElement.outerHTML.substring(0, 500) + '...' : 'No parent',
                            grandparentHTML: el.parentElement && el.parentElement.parentElement ? 
                                el.parentElement.parentElement.outerHTML.substring(0, 800) + '...' : 'No grandparent',
                            followingSiblingHTML: '',
                            priceWrapperHTML: ''
                        };
                        
                        // Look for following siblings
                        let sibling = el.parentElement ? el.parentElement.nextElementSibling : null;
                        if (sibling) {
                            result.followingSiblingHTML = sibling.outerHTML.substring(0, 400) + '...';
                        }
                        
                        // Look for price wrapper specifically
                        let current = el;
                        for (let i = 0; i < 6; i++) {
                            if (current.parentElement) {
                                current = current.parentElement;
                                let priceWrapper = current.querySelector('.cc-priceWrapper_8d8617');
                                if (priceWrapper) {
                                    result.priceWrapperHTML = priceWrapper.outerHTML.substring(0, 600) + '...';
                                    break;
                                }
                            }
                        }
                        
                        return result;
                    }
                """)
                
                print(f"Product element: {dom_structure['elementHTML']}")
                print(f"Parent: {dom_structure['parentHTML']}")
                print(f"Grandparent: {dom_structure['grandparentHTML']}")
                if dom_structure['followingSiblingHTML']:
                    print(f"Following sibling: {dom_structure['followingSiblingHTML']}")
                if dom_structure['priceWrapperHTML']:
                    print(f"Price wrapper: {dom_structure['priceWrapperHTML']}")
                
                # Try to find offers using different strategies
                print(f"\n🔍 Searching for offers related to this product:")
                
                # Strategy: Look in the same container that has this product
                offer_found = product_element.evaluate("""
                    el => {
                        // Try multiple levels up to find offers
                        let current = el;
                        for (let i = 0; i < 8; i++) {
                            if (current.parentElement) {
                                current = current.parentElement;
                                let offers = current.querySelectorAll('span.sn-title_522dc0');
                                if (offers.length > 0) {
                                    let result = [];
                                    offers.forEach(offer => {
                                        let text = offer.textContent.trim();
                                        if (text && !text.includes('%') && !text.startsWith('up to')) {
                                            result.push({
                                                text: text,
                                                html: offer.outerHTML,
                                                level: i
                                            });
                                        }
                                    });
                                    if (result.length > 0) {
                                        return result;
                                    }
                                }
                            }
                        }
                        return [];
                    }
                """)
                
                if offer_found and len(offer_found) > 0:
                    for offer in offer_found:
                        print(f"   ✅ Found offer: '{offer['text']}' at level {offer['level']}")
                        print(f"      HTML: {offer['html']}")
                else:
                    print(f"   ❌ No offers found for this product")
                    
            else:
                print(f"❌ Product not found: '{product_name}'")
        
        playwright_manager.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 Advanced Product-Offer Relationship Debug")
    print("=" * 60)
    debug_product_offer_relationship()
