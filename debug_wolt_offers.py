"""
Debug script to test Wolt offer extraction
Testing the HTML structure for offers on Wolt pages.
"""
import asyncio
from playwright.async_api import async_playwright
import re

async def debug_wolt_offers():
    """Debug Wolt offer extraction with the provided examples."""
    
    test_urls = [
        "https://wolt.com/en/cyp/nicosia/restaurant/kfc-nikis",
        "https://wolt.com/en/cyp/nicosia/restaurant/pizza-hut-kennedy"
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to False to see the browser
        
        for url in test_urls:
            print(f"\n🔍 Testing: {url}")
            
            page = await browser.new_page()
            
            try:
                # Navigate to page
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)  # Wait for JavaScript to load
                
                # Look for the offer span elements
                offer_spans = await page.query_selector_all('span.byr4db3')
                print(f"Found {len(offer_spans)} offer spans with class 'byr4db3'")
                
                for i, span in enumerate(offer_spans):
                    text = await span.text_content()
                    print(f"  Offer {i+1}: '{text}'")
                
                # Look for products and their containers
                product_cards = await page.query_selector_all('[data-test-id="horizontal-item-card"]')
                print(f"Found {len(product_cards)} product cards")
                
                # Check first few products for offers
                for i, card in enumerate(product_cards[:5]):
                    # Get product name
                    name_element = await card.query_selector('h3[data-test-id="horizontal-item-card-header"]')
                    if name_element:
                        name = await name_element.text_content()
                        print(f"\n  Product {i+1}: {name}")
                        
                        # Look for offer spans within this card
                        offer_spans_in_card = await card.query_selector_all('span.byr4db3')
                        if offer_spans_in_card:
                            for j, offer_span in enumerate(offer_spans_in_card):
                                offer_text = await offer_span.text_content()
                                print(f"    Offer {j+1}: '{offer_text}'")
                        else:
                            print("    No offers found")
                
                # Try alternative selectors for offers
                print("\n🔍 Trying alternative offer selectors...")
                
                # Look for discount badges
                discount_elements = await page.query_selector_all('[class*="discount"], [class*="offer"], [class*="badge"]')
                print(f"Found {len(discount_elements)} potential discount elements")
                
                for i, elem in enumerate(discount_elements[:10]):
                    text = await elem.text_content()
                    classes = await elem.get_attribute('class')
                    if text and text.strip():
                        print(f"  Discount element {i+1}: '{text.strip()}' (classes: {classes})")
                
            except Exception as e:
                print(f"❌ Error processing {url}: {e}")
            
            finally:
                await page.close()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_wolt_offers())
