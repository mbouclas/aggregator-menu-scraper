#!/usr/bin/env python3
"""
Test Offer Calculation Logic
===========================
Analyze the Caffè Nero JSON file to understand offer patterns and test calculations.
"""

import json
from collections import defaultdict

def analyze_caffe_nero_offers():
    """Analyze offer patterns in the Caffè Nero JSON file."""
    with open('output/foody_caffè-nero.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    products = data.get('products', [])
    
    print("🔍 Analyzing Caffè Nero Offer Patterns")
    print("=" * 60)
    
    # Categorize products by offer patterns
    patterns = {
        'discount_no_name': [],  # discount_percentage > 0 but offer_name empty
        'name_no_discount': [],  # offer_name exists but discount_percentage = 0
        'both_present': [],      # both discount_percentage > 0 and offer_name
        'neither': []           # no discount and no offer name
    }
    
    for product in products:
        discount_pct = float(product.get('discount_percentage', 0))
        offer_name = product.get('offer_name', '').strip()
        
        if discount_pct > 0 and not offer_name:
            patterns['discount_no_name'].append(product)
        elif offer_name and discount_pct == 0:
            patterns['name_no_discount'].append(product)
        elif discount_pct > 0 and offer_name:
            patterns['both_present'].append(product)
        else:
            patterns['neither'].append(product)
    
    print(f"📊 Pattern Analysis:")
    print(f"   Total products: {len(products)}")
    print(f"   Discount % only (no name): {len(patterns['discount_no_name'])}")
    print(f"   Offer name only (no discount): {len(patterns['name_no_discount'])}")
    print(f"   Both discount & name: {len(patterns['both_present'])}")
    print(f"   Neither: {len(patterns['neither'])}")
    
    # Show examples of each pattern
    if patterns['discount_no_name']:
        print(f"\n🎯 Example: Discount % only (no name):")
        example = patterns['discount_no_name'][0]
        print(f"   Product: {example['name']}")
        print(f"   Price: €{example['price']}")
        print(f"   Original: €{example['original_price']}")
        print(f"   Discount: {example['discount_percentage']}%")
        print(f"   Offer Name: '{example['offer_name']}'")
    
    if patterns['name_no_discount']:
        print(f"\n🏷️  Example: Offer name only (no discount):")
        example = patterns['name_no_discount'][0]
        print(f"   Product: {example['name']}")
        print(f"   Price: €{example['price']}")
        print(f"   Original: €{example['original_price']}")
        print(f"   Discount: {example['discount_percentage']}%")
        print(f"   Offer Name: '{example['offer_name']}'")
    
    # Test current import logic
    print(f"\n🧪 Testing Current Import Logic:")
    offers_found_current = {}
    
    for product in products:
        offer_name = product.get('offer_name', '').strip()
        discount_pct = float(product.get('discount_percentage', 0))
        
        # Current logic: only when offer_name exists
        if offer_name:
            if offer_name not in offers_found_current:
                offers_found_current[offer_name] = {
                    'discount_percentage': discount_pct,
                    'product_count': 0
                }
            offers_found_current[offer_name]['product_count'] += 1
    
    print(f"   Current logic finds: {len(offers_found_current)} offers")
    for offer_name, details in offers_found_current.items():
        print(f"   • '{offer_name}' - {details['discount_percentage']}% - {details['product_count']} products")
    
    # Test improved logic
    print(f"\n✨ Testing Improved Import Logic:")
    offers_found_improved = {}
    
    for product in products:
        offer_name = product.get('offer_name', '').strip()
        discount_pct = float(product.get('discount_percentage', 0))
        
        # Improved logic: create offer for any product with discount or offer name
        if offer_name:
            # Use explicit offer name
            if offer_name not in offers_found_improved:
                offers_found_improved[offer_name] = {
                    'discount_percentage': discount_pct,
                    'product_count': 0,
                    'type': 'named_offer'
                }
            offers_found_improved[offer_name]['product_count'] += 1
        elif discount_pct > 0:
            # Create offer name from discount percentage
            auto_offer_name = f"{int(discount_pct)}% Discount"
            if auto_offer_name not in offers_found_improved:
                offers_found_improved[auto_offer_name] = {
                    'discount_percentage': discount_pct,
                    'product_count': 0,
                    'type': 'auto_generated'
                }
            offers_found_improved[auto_offer_name]['product_count'] += 1
    
    print(f"   Improved logic finds: {len(offers_found_improved)} offers")
    for offer_name, details in offers_found_improved.items():
        print(f"   • '{offer_name}' - {details['discount_percentage']}% - {details['product_count']} products ({details['type']})")
    
    # Calculate discount amounts
    print(f"\n💰 Discount Amount Calculations:")
    for product in patterns['discount_no_name'][:3]:  # Show first 3 examples
        price = float(product['price'])
        original = float(product['original_price'])
        discount_pct = float(product['discount_percentage'])
        
        # The current data shows price = original_price, but discount_percentage exists
        # This means we need to calculate the original price from the discount
        if price == original and discount_pct > 0:
            # Calculate what the original price should be
            calculated_original = price / (1 - discount_pct/100)
            discount_amount = calculated_original - price
            
            print(f"   Product: {product['name'][:40]}...")
            print(f"     Current price: €{price}")
            print(f"     Stored original: €{original} (same as price - wrong!)")
            print(f"     Calculated original: €{calculated_original:.2f}")
            print(f"     Discount amount: €{discount_amount:.2f}")
            print(f"     Discount %: {discount_pct}%")
            print()

if __name__ == '__main__':
    analyze_caffe_nero_offers()
