#!/usr/bin/env python3
"""
Simple Offer Analysis
====================
Analyze offer data in JSON files without database dependencies.
"""

import json
import sys

def analyze_offers_in_file(file_path):
    """Analyze offers in a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {file_path}: {e}")
        return
    
    restaurant_name = data.get('restaurant', {}).get('name', 'Unknown')
    products = data.get('products', [])
    
    # Analyze offer patterns
    offers_found = {}
    products_with_offers = 0
    total_discount_amount = 0
    
    for product in products:
        offer_name = product.get('offer_name', '').strip()
        discount_pct = float(product.get('discount_percentage', 0))
        price = float(product.get('price', 0))
        original_price = float(product.get('original_price', 0))
        
        # Determine final offer name (using fixed logic)
        final_offer_name = None
        if offer_name:
            final_offer_name = offer_name
        elif discount_pct > 0:
            final_offer_name = f"{int(discount_pct)}% Discount"
        
        if final_offer_name:
            products_with_offers += 1
            
            if final_offer_name not in offers_found:
                offers_found[final_offer_name] = {
                    'discount_percentage': discount_pct,
                    'product_count': 0,
                    'total_savings': 0,
                    'type': 'explicit' if offer_name else 'auto_generated'
                }
            
            offers_found[final_offer_name]['product_count'] += 1
            
            # Calculate discount amount with corrected original price
            if discount_pct > 0 and price == original_price:
                corrected_original = price / (1 - discount_pct/100)
                discount_amount = corrected_original - price
            else:
                discount_amount = max(0, original_price - price)
            
            offers_found[final_offer_name]['total_savings'] += discount_amount
            total_discount_amount += discount_amount
    
    # Print results
    print(f"\n📊 Offer Analysis: {restaurant_name}")
    print(f"📁 File: {file_path}")
    print("=" * 60)
    print(f"🛍️  Total products: {len(products)}")
    print(f"🎁 Products with offers: {products_with_offers}")
    print(f"🏷️  Unique offers found: {len(offers_found)}")
    print(f"💰 Total potential savings: €{total_discount_amount:.2f}")
    
    if offers_found:
        print(f"\n🎯 Offer Details:")
        for offer_name, details in offers_found.items():
            print(f"   • {offer_name} ({details['type']})")
            print(f"     - Discount: {details['discount_percentage']}%")
            print(f"     - Products: {details['product_count']}")
            print(f"     - Total savings: €{details['total_savings']:.2f}")
    else:
        print("   No offers found in this file")
    
    return offers_found

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python simple_offer_analysis.py <json_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    analyze_offers_in_file(file_path)
