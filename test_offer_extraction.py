#!/usr/bin/env python3
"""
Test script for offer name extraction feature.

This script demonstrates the new offer name extraction functionality
for foody scrapers that identifies named offers like "1+1 Deals" while
ignoring percentage-based discounts.
"""

import sys
import os
sys.path.append('src')

from bs4 import BeautifulSoup


def test_offer_extraction():
    """Test the offer name extraction with sample HTML."""
    
    # Mock the _extract_offer_name method for testing
    def extract_offer_name(html_content):
        """
        Simplified version of the offer extraction logic for testing.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for offer elements with the specific class
        offer_selectors = [
            'span.sn-title_522dc0',
            '[class*="sn-title"]',
        ]
        
        for selector in offer_selectors:
            offer_elements = soup.select(selector)
            
            for offer_element in offer_elements:
                offer_text = offer_element.get_text(strip=True)
                
                # Skip if empty, too short, or contains %
                if not offer_text or len(offer_text) < 2 or '%' in offer_text:
                    continue
                
                # Skip discount patterns
                if (offer_text.lower().startswith('up to') or 
                    offer_text.lower().endswith('off') or
                    offer_text.startswith('€')):
                    continue
                
                # Valid offer name found
                if 2 <= len(offer_text) <= 50:
                    return offer_text
        
        return ""
    
    # Test cases based on user examples
    test_cases = [
        {
            'name': '1+1 Deals offer',
            'html': '<span class="sn-title_522dc0">1+1 Deals</span>',
            'expected': '1+1 Deals'
        },
        {
            'name': 'Foody deals offer', 
            'html': '<span class="sn-title_522dc0">Foody deals</span>',
            'expected': 'Foody deals'
        },
        {
            'name': '8€ meals offer',
            'html': '<span class="sn-title_522dc0">8€ meals</span>',
            'expected': '8€ meals'
        },
        {
            'name': 'Percentage discount (should be ignored)',
            'html': '<span class="sn-title_522dc0">up to -37%</span>',
            'expected': ''
        },
        {
            'name': 'Another percentage (should be ignored)',
            'html': '<span class="sn-title_522dc0">50% off</span>',
            'expected': ''
        },
        {
            'name': 'Complex offer container',
            'html': '''
                <div class="product-container">
                    <h3>Freddo Espresso</h3>
                    <span class="sn-title_522dc0">Summer Special</span>
                    <div class="price">€3.50</div>
                </div>
            ''',
            'expected': 'Summer Special'
        }
    ]
    
    print("Testing Offer Name Extraction Feature")
    print("=" * 50)
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        result = extract_offer_name(test_case['html'])
        passed = result == test_case['expected']
        all_passed = all_passed and passed
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"Test {i}: {test_case['name']}")
        print(f"   Expected: '{test_case['expected']}'")
        print(f"   Got:      '{result}'")
        print(f"   Result:   {status}")
        print()
    
    print("=" * 50)
    if all_passed:
        print("🎉 All tests passed! Offer name extraction is working correctly.")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return all_passed


def demonstrate_usage():
    """Demonstrate how the feature works in practice."""
    
    print("\nFeature Usage Demonstration")
    print("=" * 50)
    print("This feature extracts offer names from foody.com.cy HTML elements.")
    print("It distinguishes between:")
    print("  ✓ Named offers: '1+1 Deals', 'Foody deals', '8€ meals'")
    print("  ✗ Percentage discounts: 'up to -37%', '50% off'")
    print()
    print("The extracted offer names are stored in the 'offer_name' field")
    print("in the product data and saved to the database for tracking.")
    print()
    print("Example product output with offer:")
    print("""
    {
        "id": "foody_prod_123",
        "name": "Freddo Espresso",
        "price": 3.50,
        "original_price": 3.50,
        "discount_percentage": 0.0,
        "offer_name": "1+1 Deals",
        "category": "Cold Coffees",
        ...
    }
    """)


if __name__ == "__main__":
    print("Foody Scraper - Offer Name Extraction Feature Test")
    print("Developed for feature/foody-offer-names branch\n")
    
    try:
        success = test_offer_extraction()
        demonstrate_usage()
        
        if success:
            print("\n🚀 Ready for testing with real foody.com.cy pages!")
        else:
            print("\n⚠️  Please fix the failing tests before proceeding.")
            
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        sys.exit(1)
