#!/usr/bin/env python3
"""
Simple test to verify exact offer extraction issue.
"""

import sys
import os
sys.path.append('src')

from src.common.fast_playwright_utils import FastPlaywrightManager, fast_page_fetch, fast_get_text_content

def test_exact_extraction():
    """Test the exact extraction on a known product with an offer."""
    
    target_url = "https://www.foody.com.cy/delivery/menu/the-big-bad-wolf"
    
    try:
        playwright_manager = FastPlaywrightManager(headless=True, timeout=15000)
        page = playwright_manager.create_fast_driver()
        
        print("📄 Loading page...")
        fast_page_fetch(page, target_url, wait_time=3)
        
        # Find the specific product that we know has "1+1 Deals"
        product_element = page.locator("h3.cc-name_acd53e:has-text('1+1 Giant Greek Pita')").first
        
        if product_element.count() > 0:
            print("✅ Found product: '1+1 Giant Greek Pita'")
            
            # Test our exact extraction logic step by step
            print("\n🔍 Testing extraction logic step by step:")
            
            # Step 1: Get parent
            parent_exists = product_element.evaluate("el => el.parentElement ? true : false")
            print(f"Step 1 - Parent exists: {parent_exists}")
            
            if parent_exists:
                # Step 2: Look for priceWrapper in parent
                price_wrapper_exists = product_element.evaluate("""
                    el => el.parentElement.querySelector('.cc-priceWrapper_8d8617') ? true : false
                """)
                print(f"Step 2 - Price wrapper exists: {price_wrapper_exists}")
                
                if price_wrapper_exists:
                    # Step 3: Look for offer in priceWrapper
                    offer_exists = product_element.evaluate("""
                        el => {
                            let priceWrapper = el.parentElement.querySelector('.cc-priceWrapper_8d8617');
                            return priceWrapper.querySelector('span.sn-title_522dc0') ? true : false;
                        }
                    """)
                    print(f"Step 3 - Offer span exists: {offer_exists}")
                    
                    if offer_exists:
                        # Step 4: Get the offer text
                        offer_text = product_element.evaluate("""
                            el => {
                                let priceWrapper = el.parentElement.querySelector('.cc-priceWrapper_8d8617');
                                let offerSpan = priceWrapper.querySelector('span.sn-title_522dc0');
                                return offerSpan ? offerSpan.textContent.trim() : 'NO TEXT';
                            }
                        """)
                        print(f"Step 4 - Offer text: '{offer_text}'")
                        
                        # Step 5: Validate the text
                        if offer_text and offer_text != 'NO TEXT':
                            has_percent = '%' in offer_text
                            starts_with_up_to = offer_text.lower().startswith('up to')
                            is_valid_length = 2 <= len(offer_text) <= 50
                            
                            print(f"Step 5 - Validation:")
                            print(f"  Has percent: {has_percent}")
                            print(f"  Starts with 'up to': {starts_with_up_to}")
                            print(f"  Valid length: {is_valid_length}")
                            print(f"  Should be valid: {not has_percent and not starts_with_up_to and is_valid_length}")
                        else:
                            print("Step 5 - No text found")
                    else:
                        print("Step 3 - No offer span found")
                else:
                    print("Step 2 - No price wrapper found")
            else:
                print("Step 1 - No parent found")
            
            # Also test if the fast_get_text_content function works
            print("\n🔍 Testing fast_get_text_content function:")
            try:
                offer_element = page.locator("span.sn-title_522dc0:has-text('1+1 Deals')").first
                if offer_element.count() > 0:
                    text_via_function = fast_get_text_content(offer_element)
                    text_via_direct = offer_element.text_content()
                    print(f"Via fast_get_text_content: '{text_via_function}'")
                    print(f"Via direct text_content: '{text_via_direct}'")
                else:
                    print("Offer element not found directly")
            except Exception as e:
                print(f"Error testing fast_get_text_content: {e}")
        else:
            print("❌ Product not found")
        
        playwright_manager.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 Testing Exact Offer Extraction Logic")
    print("=" * 50)
    test_exact_extraction()
