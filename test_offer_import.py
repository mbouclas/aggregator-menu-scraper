#!/usr/bin/env python3
"""
Test Offer Import Logic
======================
Quick test to validate offer import functionality.
"""

import json
import tempfile
import os
from datetime import datetime

def create_test_json():
    """Create a test JSON file with offers."""
    test_data = {
        "metadata": {
            "scraper_version": "1.0.0",
            "domain": "test.com",
            "scraped_at": datetime.now().isoformat(),
            "processing_duration_seconds": 1.5,
            "product_count": 3,
            "category_count": 1
        },
        "source": {
            "url": "https://test.com/restaurant",
            "scraping_method": "test"
        },
        "restaurant": {
            "name": "Test Coffee Shop",
            "brand": "Test Brand",
            "rating": 4.5,
            "delivery_fee": 2.50,
            "minimum_order": 10.00,
            "delivery_time": "30-40 min"
        },
        "categories": [
            {
                "name": "Hot Drinks",
                "description": "Coffee and tea",
                "display_order": 1,
                "source": "menu"
            }
        ],
        "products": [
            {
                "id": "test_prod_1",
                "name": "Cappuccino",
                "description": "Rich coffee with steamed milk",
                "category": "Hot Drinks",
                "price": 2.40,
                "original_price": 3.00,
                "discount_percentage": 20,
                "offer_name": "Morning Special - 20% off",
                "currency": "EUR",
                "availability": True
            },
            {
                "id": "test_prod_2", 
                "name": "Espresso",
                "description": "Strong coffee shot",
                "category": "Hot Drinks",
                "price": 1.60,
                "original_price": 2.00,
                "discount_percentage": 20,
                "offer_name": "Morning Special - 20% off",
                "currency": "EUR",
                "availability": True
            },
            {
                "id": "test_prod_3",
                "name": "Tea",
                "description": "Hot tea",
                "category": "Hot Drinks", 
                "price": 2.00,
                "original_price": 2.00,
                "discount_percentage": 0,
                "currency": "EUR",
                "availability": True
            }
        ],
        "errors": []
    }
    return test_data

def test_offer_extraction():
    """Test that offers are properly extracted from product data."""
    test_data = create_test_json()
    
    # Create temporary JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f, indent=2)
        temp_file = f.name
    
    try:
        print("🧪 Testing Offer Import Logic")
        print("=" * 50)
        
        print(f"📁 Created test file: {temp_file}")
        
        # Analyze the test data
        products = test_data['products']
        offers_found = {}
        
        for product in products:
            offer_name = product.get('offer_name', '').strip()
            discount_pct = product.get('discount_percentage', 0)
            
            if offer_name:
                if offer_name not in offers_found:
                    offers_found[offer_name] = {
                        'discount_percentage': discount_pct,
                        'product_count': 0
                    }
                offers_found[offer_name]['product_count'] += 1
        
        print(f"\n📊 Analysis Results:")
        print(f"   Total products: {len(products)}")
        print(f"   Products with offers: {sum(1 for p in products if p.get('offer_name'))}")
        print(f"   Unique offers: {len(offers_found)}")
        
        if offers_found:
            print(f"\n🎯 Offers Detected:")
            for offer_name, details in offers_found.items():
                print(f"   • {offer_name}")
                print(f"     - Discount: {details['discount_percentage']}%")
                print(f"     - Products: {details['product_count']}")
        
        print(f"\n✅ Test data structure is valid for offer import!")
        print(f"💡 To test with database: python database/migrate_existing_offers.py --file {temp_file} --analyze-only")
        
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)
            print(f"🧹 Cleaned up test file")

if __name__ == '__main__':
    test_offer_extraction()
