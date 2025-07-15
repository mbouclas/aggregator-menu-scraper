#!/usr/bin/env python3
"""
Test Offer Deactivation
=======================
Create a modified Caffè Nero file to test offer deactivation logic.
"""

import json
from copy import deepcopy

def create_modified_caffe_nero():
    """Create a modified version of the Caffè Nero file to test offer deactivation."""
    
    # Load original file
    with open('output/foody_caffè-nero.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create modified version where some offers are removed
    modified_data = deepcopy(data)
    
    # Remove discount from products that had 25% discount (should deactivate that offer)
    products_modified = 0
    for product in modified_data['products']:
        if product.get('discount_percentage') == 25:
            product['discount_percentage'] = 0
            product['original_price'] = product['price']  # No discount means price = original
            products_modified += 1
            
            if products_modified >= 3:  # Modify only first 3 products
                break
    
    # Add a new offer to some products
    for i, product in enumerate(modified_data['products'][:2]):
        if product.get('discount_percentage') == 0:
            product['discount_percentage'] = 40
            product['offer_name'] = 'New Flash Sale'
            # Calculate new original price
            current_price = float(product['price'])
            product['original_price'] = current_price / (1 - 40/100)
    
    # Change metadata to simulate a new scrape
    modified_data['metadata']['scraped_at'] = '2025-07-15T15:30:00Z'
    modified_data['metadata']['processed_at'] = '2025-07-15T15:31:00Z'
    
    # Save modified file
    with open('output/foody_caffè-nero_modified.json', 'w', encoding='utf-8') as f:
        json.dump(modified_data, f, indent=2, ensure_ascii=False)
    
    print("✅ Created modified Caffè Nero file for testing offer deactivation")
    print(f"   📁 File: output/foody_caffè-nero_modified.json")
    print(f"   🔧 Removed 25% discount from {products_modified} products")
    print(f"   🆕 Added 'New Flash Sale' (40%) offer to 2 products")
    
    return 'output/foody_caffè-nero_modified.json'

if __name__ == '__main__':
    create_modified_caffe_nero()
