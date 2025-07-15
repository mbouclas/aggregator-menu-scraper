#!/usr/bin/env python3
"""
Test Fixed Offer Import Logic
============================
Test the corrected offer import logic with the Caffè Nero data.
"""

import json
import tempfile
import os
from datetime import datetime

def create_test_data_from_caffe_nero():
    """Extract sample offer data from Caffè Nero file for testing."""
    with open('output/foody_caffè-nero.json', 'r', encoding='utf-8') as f:
        original_data = json.load(f)
    
    # Find products with offers
    offer_products = []
    for product in original_data.get('products', []):
        discount_pct = float(product.get('discount_percentage', 0))
        offer_name = product.get('offer_name', '').strip()
        
        if discount_pct > 0 or offer_name:
            offer_products.append(product)
    
    # Create test data with just the offer products
    test_data = {
        "metadata": {
            "scraper_version": "1.0.0",
            "domain": "foody.com.cy",
            "scraped_at": datetime.now().isoformat(),
            "processing_duration_seconds": 1.0,
            "product_count": len(offer_products),
            "category_count": 1
        },
        "source": {
            "url": "https://foody.com.cy/test",
            "scraping_method": "test"
        },
        "restaurant": {
            "name": "Test Caffè Nero",
            "brand": "Caffè Nero",
            "rating": 4.5,
            "delivery_fee": 2.50,
            "minimum_order": 10.00,
            "delivery_time": "30-40 min"
        },
        "categories": [
            {
                "name": "Test Offers",
                "description": "Products with offers",
                "display_order": 1,
                "source": "test"
            }
        ],
        "products": [],
        "errors": []
    }
    
    # Add offer products with corrected category
    for i, product in enumerate(offer_products):
        test_product = product.copy()
        test_product['id'] = f"test_prod_{i+1}"
        test_product['category'] = "Test Offers"
        test_data['products'].append(test_product)
    
    return test_data

def simulate_improved_offer_processing(test_data):
    """Simulate the improved offer processing logic."""
    products = test_data['products']
    restaurant_name = test_data['restaurant']['name']
    
    print(f"🧪 Testing Improved Offer Logic on {restaurant_name}")
    print("=" * 70)
    
    # Step 1: Extract offers (simulating _import_offers)
    offers_found = {}
    offer_mapping = {}
    
    for product in products:
        offer_name = product.get('offer_name', '').strip()
        discount_pct = float(product.get('discount_percentage', 0))
        
        # Pattern 1: Explicit offer name
        if offer_name:
            if offer_name not in offers_found:
                offers_found[offer_name] = {
                    'discount_percentage': discount_pct,
                    'product_count': 0,
                    'type': 'explicit',
                    'offer_id': f"offer_{len(offers_found)+1}"
                }
                offer_mapping[offer_name] = offers_found[offer_name]['offer_id']
            offers_found[offer_name]['product_count'] += 1
        
        # Pattern 2: Auto-generate from discount percentage
        elif discount_pct > 0:
            auto_offer_name = f"{int(discount_pct)}% Discount"
            if auto_offer_name not in offers_found:
                offers_found[auto_offer_name] = {
                    'discount_percentage': discount_pct,
                    'product_count': 0,
                    'type': 'auto_generated',
                    'offer_id': f"offer_{len(offers_found)+1}"
                }
                offer_mapping[auto_offer_name] = offers_found[auto_offer_name]['offer_id']
            offers_found[auto_offer_name]['product_count'] += 1
    
    print(f"📊 Offers Extracted: {len(offers_found)}")
    for offer_name, details in offers_found.items():
        print(f"   • '{offer_name}' ({details['type']})")
        print(f"     - Discount: {details['discount_percentage']}%")
        print(f"     - Products: {details['product_count']}")
        print(f"     - Offer ID: {details['offer_id']}")
    
    # Step 2: Process products with corrected calculations
    print(f"\n💰 Product Processing with Corrections:")
    processed_products = []
    
    for product in products:
        offer_name = product.get('offer_name', '').strip()
        discount_pct = float(product.get('discount_percentage', 0))
        price = float(product.get('price', 0))
        original_price = float(product.get('original_price', 0))
        
        # Determine offer link
        final_offer_name = None
        offer_id = None
        
        if offer_name:
            final_offer_name = offer_name
            offer_id = offer_mapping.get(offer_name)
        elif discount_pct > 0:
            final_offer_name = f"{int(discount_pct)}% Discount"
            offer_id = offer_mapping.get(final_offer_name)
        
        # Correct original price calculation
        corrected_original = original_price
        discount_amount = 0
        
        if discount_pct > 0 and price == original_price:
            # Calculate correct original price
            corrected_original = price / (1 - discount_pct/100)
            discount_amount = corrected_original - price
        elif price < original_price:
            discount_amount = original_price - price
        
        processed_product = {
            'name': product['name'],
            'price': price,
            'original_price': corrected_original,
            'discount_percentage': discount_pct,
            'discount_amount': discount_amount,
            'offer_name': final_offer_name,
            'offer_id': offer_id
        }
        processed_products.append(processed_product)
        
        print(f"   Product: {product['name'][:40]}...")
        print(f"     Price: €{price:.2f}")
        print(f"     Original (raw): €{original_price:.2f}")
        print(f"     Original (corrected): €{corrected_original:.2f}")
        print(f"     Discount: {discount_pct}% (€{discount_amount:.2f})")
        print(f"     Offer: '{final_offer_name}' (ID: {offer_id})")
        print()
    
    return offers_found, processed_products

def main():
    """Main test function."""
    print("🔍 Testing Fixed Offer Import Logic with Caffè Nero Data")
    print("=" * 80)
    
    # Create test data from real Caffè Nero file
    test_data = create_test_data_from_caffe_nero()
    
    print(f"📁 Test data created:")
    print(f"   Restaurant: {test_data['restaurant']['name']}")
    print(f"   Products with offers: {len(test_data['products'])}")
    
    # Test the improved logic
    offers, products = simulate_improved_offer_processing(test_data)
    
    # Summary
    print(f"✅ Test Results Summary:")
    print(f"   Offers created: {len(offers)}")
    print(f"   Products processed: {len(products)}")
    print(f"   Products with offer links: {sum(1 for p in products if p['offer_id'])}")
    print(f"   Products with discount amounts: {sum(1 for p in products if p['discount_amount'] > 0)}")
    
    # Save test file for actual import testing
    test_file = 'test_caffe_nero_offers.json'
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, indent=2)
    
    print(f"\n💾 Test file saved: {test_file}")
    print(f"💡 To test with database:")
    print(f"   python database/migrate_existing_offers.py --file {test_file} --analyze-only")
    print(f"   python database/import_data.py --file {test_file}")

if __name__ == '__main__':
    main()
