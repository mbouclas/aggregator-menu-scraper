#!/usr/bin/env python3
"""
Fixed Import Logic
=================

This file contains the improved _ensure_product method that prevents duplicates.
The fix implements name-based fallback lookup to prevent creating duplicate products
with the same name but different external_ids.
"""

import uuid
import json
from typing import Dict, Any

def _ensure_product_fixed(cur, restaurant_id: str, category_mapping: Dict[str, str],
                         product_data: Dict[str, Any]) -> tuple[str, bool]:
    """
    Fixed version of _ensure_product that prevents duplicates.
    
    Returns: (product_id, was_created)
    """
    external_id = product_data['id']
    product_name = product_data['name']
    category_name = product_data.get('category', 'Uncategorized')
    category_id = category_mapping.get(category_name, category_mapping.get('Uncategorized'))
    
    if not category_id:
        raise ValueError(f"Category '{category_name}' not found and no Uncategorized fallback")
    
    # Step 1: Try to find by external_id (if provided)
    if external_id:
        cur.execute("SELECT id, name FROM products WHERE restaurant_id = %s AND external_id = %s", 
                   (restaurant_id, external_id))
        result = cur.fetchone()
        
        if result:
            # Found by external_id, check if name changed
            if result['name'] != product_name:
                print(f"⚠️  Product name changed: '{result['name']}' → '{product_name}' (external_id: {external_id})")
                # Update the name
                cur.execute("UPDATE products SET name = %s, updated_at = NOW() WHERE id = %s",
                           (product_name, result['id']))
            return result['id'], False
    
    # Step 2: Check for existing product with same name (prevent duplicates)
    cur.execute("SELECT id, external_id FROM products WHERE restaurant_id = %s AND name = %s", 
               (restaurant_id, product_name))
    existing_by_name = cur.fetchall()
    
    if existing_by_name:
        # Found product(s) with same name
        if len(existing_by_name) == 1:
            existing_product = existing_by_name[0]
            existing_external_id = existing_product['external_id']
            
            if external_id and existing_external_id and existing_external_id != external_id:
                # Same name, different external_id - update external_id
                print(f"🔄 Updating external_id: '{existing_external_id}' → '{external_id}' for product '{product_name}'")
                cur.execute("UPDATE products SET external_id = %s, updated_at = NOW() WHERE id = %s",
                           (external_id, existing_product['id']))
            elif external_id and not existing_external_id:
                # Same name, existing has NULL external_id - set external_id
                print(f"🔄 Setting external_id: NULL → '{external_id}' for product '{product_name}'")
                cur.execute("UPDATE products SET external_id = %s, updated_at = NOW() WHERE id = %s",
                           (external_id, existing_product['id']))
            
            return existing_product['id'], False
        else:
            # Multiple products with same name - this should not happen with proper uniqueness
            print(f"⚠️  Found {len(existing_by_name)} products with name '{product_name}' - using first one")
            return existing_by_name[0]['id'], False
    
    # Step 3: No existing product found - create new one
    product_id = str(uuid.uuid4())
    options = product_data.get('options', [])
    if isinstance(options, str):
        try:
            options = json.loads(options)
        except:
            options = []
    
    print(f"✅ Creating new product: '{product_name}' (external_id: {external_id})")
    
    cur.execute("""
        INSERT INTO products (
            id, restaurant_id, category_id, external_id, name, description,
            image_url, options
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        product_id, restaurant_id, category_id, external_id,
        product_name, 
        product_data.get('description', ''),
        product_data.get('image_url', ''),
        json.dumps(options)
    ))
    
    return product_id, True

def analyze_fix_benefits():
    """Analyze the benefits of the fixed logic."""
    print("🛠️  FIXED LOGIC BENEFITS")
    print("=" * 30)
    
    print("\n✅ DUPLICATE PREVENTION:")
    print("1. Name-based lookup prevents same-name products with different external_ids")
    print("2. external_id updates instead of creating duplicates")
    print("3. NULL external_id handling prevents multiple NULL duplicates")
    
    print("\n✅ DATA INTEGRITY:")
    print("1. Product names can be updated if they change")
    print("2. external_id can be updated if it changes")
    print("3. Maintains referential integrity for price records")
    
    print("\n✅ LOGGING & MONITORING:")
    print("1. Logs when product names change")
    print("2. Logs when external_ids are updated")
    print("3. Logs when new products are created")
    
    print("\n📊 SCENARIOS HANDLED:")
    print("Scenario A: Same product, same external_id → Finds existing (unchanged)")
    print("Scenario B: Same name, different external_id → Updates external_id")
    print("Scenario C: Same name, NULL external_id → Sets external_id")
    print("Scenario D: Different name, same external_id → Updates name")
    print("Scenario E: New product → Creates new product")

if __name__ == "__main__":
    analyze_fix_benefits()
