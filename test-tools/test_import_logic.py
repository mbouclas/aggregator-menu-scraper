#!/usr/bin/env python3
"""
Test Import Logic Tool
=====================

This tool simulates the import process to identify how duplicates are created.
It analyzes the _ensure_product and _import_products_and_prices logic.
"""

import psycopg2
import psycopg2.extras
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from collections import defaultdict
from datetime import datetime

def load_db_config():
    """Load database configuration from database/.env file."""
    env_path = Path(__file__).parent.parent / 'database' / '.env'
    load_dotenv(env_path)
    
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'scraper_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres123')
    }

def connect_to_db():
    """Connect to PostgreSQL database."""
    config = load_db_config()
    return psycopg2.connect(**config)

def simulate_ensure_product(restaurant_id, external_id, name, description, category):
    """Simulate the _ensure_product method to see how it behaves."""
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    print(f"\n🔍 Simulating _ensure_product for:")
    print(f"   Restaurant ID: {restaurant_id}")
    print(f"   External ID: {external_id}")
    print(f"   Name: {name}")
    print(f"   Description: {description}")
    print(f"   Category: {category}")
    
    # Step 1: Check if product exists by restaurant_id + external_id (current logic)
    if external_id:
        cur.execute("""
            SELECT id, name, description 
            FROM products 
            WHERE restaurant_id = %s AND external_id = %s
        """, (restaurant_id, external_id))
        existing_by_external_id = cur.fetchone()
        
        if existing_by_external_id:
            print(f"   ✅ Found existing product by external_id: {existing_by_external_id['id']}")
            print(f"      Existing name: {existing_by_external_id['name']}")
            print(f"      New name: {name}")
            if existing_by_external_id['name'] != name:
                print(f"      ⚠️  NAME MISMATCH DETECTED!")
            conn.close()
            return existing_by_external_id['id'], False
    
    # Step 2: Check if product exists by restaurant_id + name (missing logic)
    cur.execute("""
        SELECT id, external_id, name, description 
        FROM products 
        WHERE restaurant_id = %s AND name = %s
    """, (restaurant_id, name))
    existing_by_name = cur.fetchall()
    
    if existing_by_name:
        print(f"   ⚠️  Found {len(existing_by_name)} existing product(s) with same name:")
        for product in existing_by_name:
            print(f"      Product ID: {product['id']}, External ID: {product['external_id']}")
        print(f"   🚨 DUPLICATE CREATION SCENARIO: Same name, different external_id!")
        
        # This is where duplicates would be created in the current logic
        if not external_id:
            print(f"   🚨 NULL external_id would create duplicate!")
        elif external_id not in [p['external_id'] for p in existing_by_name]:
            print(f"   🚨 Different external_id would create duplicate!")
    
    # Step 3: Show what would happen (we won't actually create)
    print(f"   📝 Current logic would CREATE NEW PRODUCT")
    print(f"      This could be a duplicate if same name exists with different external_id")
    
    conn.close()
    return None, True  # Would create new product

def test_duplicate_scenarios():
    """Test various scenarios that could create duplicates."""
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    print("\n🧪 Testing Duplicate Creation Scenarios")
    print("=" * 50)
    
    # Get some real restaurant IDs and product examples
    cur.execute("""
        SELECT DISTINCT r.id, r.name, p.name as product_name, p.external_id
        FROM restaurants r
        JOIN products p ON r.id = p.restaurant_id
        WHERE p.external_id IS NOT NULL
        LIMIT 5
    """)
    
    examples = cur.fetchall()
    
    for example in examples:
        print(f"\n📊 Scenario Test for {example['name']}")
        print("-" * 30)
        
        # Scenario 1: Same product, same external_id (should find existing)
        print("Scenario 1: Exact match (should find existing)")
        simulate_ensure_product(
            example['id'], 
            example['external_id'], 
            example['product_name'],
            "Test description",
            "Test category"
        )
        
        # Scenario 2: Same product name, different external_id (creates duplicate!)
        print("\nScenario 2: Same name, different external_id (CREATES DUPLICATE)")
        simulate_ensure_product(
            example['id'], 
            f"{example['external_id']}_different", 
            example['product_name'],
            "Test description",
            "Test category"
        )
        
        # Scenario 3: Same product name, NULL external_id (creates duplicate!)
        print("\nScenario 3: Same name, NULL external_id (CREATES DUPLICATE)")
        simulate_ensure_product(
            example['id'], 
            None, 
            example['product_name'],
            "Test description",
            "Test category"
        )
        
        break  # Just test one restaurant for now
    
    conn.close()

def analyze_current_logic_gaps():
    """Analyze the gaps in current import logic."""
    print("\n🔍 Analysis of Current Import Logic Gaps")
    print("=" * 50)
    
    print("\n📋 Current _ensure_product Logic:")
    print("1. Check: SELECT id FROM products WHERE restaurant_id = %s AND external_id = %s")
    print("2. If found: Return existing product_id")
    print("3. If NOT found: Create new product")
    
    print("\n🚨 IDENTIFIED GAPS:")
    print("1. NO CHECK for existing products with same name but different external_id")
    print("2. NO CHECK for existing products with same name but NULL external_id")
    print("3. NO VALIDATION of external_id uniqueness within restaurant")
    print("4. NO HANDLING of external_id changes over time")
    
    print("\n💡 DUPLICATE CREATION SCENARIOS:")
    print("Scenario A: Product scraped with external_id 'ABC123', name 'Pizza Margherita'")
    print("           Next scrape: Same product has external_id 'XYZ789', same name")
    print("           Result: TWO products with same name, different external_ids")
    
    print("\nScenario B: Product scraped with external_id 'ABC123', name 'Pizza Margherita'")
    print("           Next scrape: Same product has NULL external_id, same name")
    print("           Result: TWO products with same name, one with external_id, one NULL")
    
    print("\nScenario C: Product scraped with NULL external_id, name 'Pizza Margherita'")
    print("           Next scrape: Same product has NULL external_id, same name")
    print("           Result: MULTIPLE products with same name, all NULL external_id")

def propose_fix():
    """Propose a fix for the duplicate creation issue."""
    print("\n💡 PROPOSED FIX: Enhanced Product Uniqueness Logic")
    print("=" * 55)
    
    print("\n📝 New _ensure_product Logic Should Be:")
    print("1. If external_id provided:")
    print("   a. Check: SELECT id FROM products WHERE restaurant_id = %s AND external_id = %s")
    print("   b. If found: Return existing product_id")
    print("   c. If NOT found: Check for same name with different external_id")
    print("      - If same name exists: UPDATE external_id of existing product")
    print("      - If no same name: Create new product")
    print("\n2. If external_id is NULL:")
    print("   a. Check: SELECT id FROM products WHERE restaurant_id = %s AND name = %s")
    print("   b. If found: Return existing product_id (don't create duplicate)")
    print("   c. If NOT found: Create new product")
    
    print("\n🔧 Implementation Strategy:")
    print("1. Add name-based lookup as fallback")
    print("2. Add external_id update capability")
    print("3. Add uniqueness validation")
    print("4. Add logging for duplicate prevention")

if __name__ == "__main__":
    test_duplicate_scenarios()
    analyze_current_logic_gaps()
    propose_fix()
