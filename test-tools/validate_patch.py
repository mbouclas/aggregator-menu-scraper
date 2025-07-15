#!/usr/bin/env python3
"""
Validate Import Logic Patch
===========================

This tool validates that the patched import logic correctly prevents duplicates.
It performs various test scenarios to ensure the fix works properly.
"""

import psycopg2
import psycopg2.extras
import os
from pathlib import Path
from dotenv import load_dotenv
import uuid
import json
from datetime import datetime
import sys

# Add the parent directory to the path to import the DatabaseImporter
sys.path.insert(0, str(Path(__file__).parent.parent))

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

def create_test_data():
    """Create test data for validation."""
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Create a test restaurant
    test_restaurant_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO restaurants (id, name, slug, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """, (test_restaurant_id, "Test Restaurant for Validation", "test-restaurant-validation"))
    
    # Create a test category
    test_category_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO categories (id, restaurant_id, name, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        ON CONFLICT (restaurant_id, name) DO NOTHING
        RETURNING id
    """, (test_category_id, test_restaurant_id, "Test Category"))
    
    result = cur.fetchone()
    if result:
        test_category_id = result['id']
    else:
        # Category already exists, get its ID
        cur.execute("SELECT id FROM categories WHERE restaurant_id = %s AND name = %s",
                   (test_restaurant_id, "Test Category"))
        test_category_id = cur.fetchone()['id']
    
    conn.commit()
    conn.close()
    
    return test_restaurant_id, test_category_id

def test_ensure_product_scenarios():
    """Test various scenarios with the patched _ensure_product method."""
    print("🧪 Testing Patched _ensure_product Method")
    print("=" * 45)
    
    try:
        from database.import_data import ScraperDataImporter
    except ImportError:
        print("❌ Could not import ScraperDataImporter. Make sure the patch was applied correctly.")
        return False
    
    # Create test data
    test_restaurant_id, test_category_id = create_test_data()
    
    # Initialize the importer
    config = load_db_config()
    importer = ScraperDataImporter(
        host=config['host'],
        port=config['port'],
        database=config['database'],
        user=config['user'],
        password=config['password']
    )
    
    conn = importer.get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Category mapping for tests
    category_mapping = {"Test Category": test_category_id, "Uncategorized": test_category_id}
    
    print(f"\n📊 Testing with Restaurant ID: {test_restaurant_id}")
    print(f"📊 Testing with Category ID: {test_category_id}")
    
    # Test Scenario 1: Create new product
    print("\n🧪 Test 1: Create New Product")
    print("-" * 30)
    product_data_1 = {
        'id': 'test_ext_001',
        'name': 'Test Pizza Margherita',
        'description': 'Delicious test pizza',
        'category': 'Test Category'
    }
    
    product_id_1 = importer._ensure_product(cur, test_restaurant_id, category_mapping, product_data_1)
    print(f"✅ Created product with ID: {product_id_1}")
    
    # Test Scenario 2: Find existing product (same external_id)
    print("\n🧪 Test 2: Find Existing Product (Same External ID)")
    print("-" * 50)
    product_data_2 = {
        'id': 'test_ext_001',
        'name': 'Test Pizza Margherita',
        'description': 'Delicious test pizza',
        'category': 'Test Category'
    }
    
    product_id_2 = importer._ensure_product(cur, test_restaurant_id, category_mapping, product_data_2)
    print(f"✅ Found existing product with ID: {product_id_2}")
    assert product_id_1 == product_id_2, "Should return same product ID"
    
    # Test Scenario 3: Same name, different external_id (should update external_id)
    print("\n🧪 Test 3: Same Name, Different External ID (Should Update)")
    print("-" * 60)
    product_data_3 = {
        'id': 'test_ext_002',
        'name': 'Test Pizza Margherita',
        'description': 'Delicious test pizza',
        'category': 'Test Category'
    }
    
    product_id_3 = importer._ensure_product(cur, test_restaurant_id, category_mapping, product_data_3)
    print(f"✅ Updated product with ID: {product_id_3}")
    assert product_id_1 == product_id_3, "Should return same product ID"
    
    # Verify external_id was updated
    cur.execute("SELECT external_id FROM products WHERE id = %s", (product_id_1,))
    updated_external_id = cur.fetchone()['external_id']
    assert updated_external_id == 'test_ext_002', f"External ID should be updated to 'test_ext_002', got '{updated_external_id}'"
    print(f"✅ External ID correctly updated to: {updated_external_id}")
    
    # Test Scenario 4: Same name, NULL external_id (should find existing)
    print("\n🧪 Test 4: Same Name, NULL External ID (Should Find Existing)")
    print("-" * 60)
    product_data_4 = {
        'id': None,
        'name': 'Test Pizza Margherita',
        'description': 'Delicious test pizza',
        'category': 'Test Category'
    }
    
    product_id_4 = importer._ensure_product(cur, test_restaurant_id, category_mapping, product_data_4)
    print(f"✅ Found existing product with ID: {product_id_4}")
    assert product_id_1 == product_id_4, "Should return same product ID"
    
    # Test Scenario 5: Create new product with different name
    print("\n🧪 Test 5: Create New Product with Different Name")
    print("-" * 50)
    product_data_5 = {
        'id': 'test_ext_003',
        'name': 'Test Pizza Pepperoni',
        'description': 'Spicy test pizza',
        'category': 'Test Category'
    }
    
    product_id_5 = importer._ensure_product(cur, test_restaurant_id, category_mapping, product_data_5)
    print(f"✅ Created new product with ID: {product_id_5}")
    assert product_id_1 != product_id_5, "Should create different product"
    
    # Test Scenario 6: Name change for existing external_id
    print("\n🧪 Test 6: Name Change for Existing External ID")
    print("-" * 50)
    product_data_6 = {
        'id': 'test_ext_003',
        'name': 'Test Pizza Pepperoni Supreme',
        'description': 'Super spicy test pizza',
        'category': 'Test Category'
    }
    
    product_id_6 = importer._ensure_product(cur, test_restaurant_id, category_mapping, product_data_6)
    print(f"✅ Updated product name, ID: {product_id_6}")
    assert product_id_5 == product_id_6, "Should return same product ID"
    
    # Verify name was updated
    cur.execute("SELECT name FROM products WHERE id = %s", (product_id_5,))
    updated_name = cur.fetchone()['name']
    assert updated_name == 'Test Pizza Pepperoni Supreme', f"Name should be updated, got '{updated_name}'"
    print(f"✅ Product name correctly updated to: {updated_name}")
    
    # Clean up test data
    print("\n🧹 Cleaning up test data...")
    cur.execute("DELETE FROM products WHERE restaurant_id = %s", (test_restaurant_id,))
    cur.execute("DELETE FROM categories WHERE restaurant_id = %s", (test_restaurant_id,))
    cur.execute("DELETE FROM restaurants WHERE id = %s", (test_restaurant_id,))
    
    conn.commit()
    conn.close()
    
    print("\n✅ ALL TESTS PASSED!")
    print("\n📊 Test Summary:")
    print("✓ New product creation works")
    print("✓ Existing product lookup by external_id works")
    print("✓ External ID update for same-name products works")
    print("✓ NULL external_id handling works")
    print("✓ Different product creation works")
    print("✓ Product name updates work")
    
    return True

def validate_no_duplicates_in_db():
    """Validate that there are no duplicate products in the database."""
    print("\n🔍 Validating No Duplicates in Database")
    print("=" * 40)
    
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Check for products with same name in same restaurant
    cur.execute("""
        SELECT 
            restaurant_id,
            r.name as restaurant_name,
            p.name as product_name,
            COUNT(*) as duplicate_count,
            ARRAY_AGG(p.id ORDER BY p.created_at) as product_ids,
            ARRAY_AGG(p.external_id ORDER BY p.created_at) as external_ids
        FROM products p
        JOIN restaurants r ON p.restaurant_id = r.id
        GROUP BY restaurant_id, r.name, p.name
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC
        LIMIT 10
    """)
    
    duplicates = cur.fetchall()
    
    if duplicates:
        print(f"⚠️  Found {len(duplicates)} sets of duplicate products:")
        for dup in duplicates:
            print(f"  🏪 {dup['restaurant_name']}")
            print(f"     Product: '{dup['product_name']}'")
            print(f"     Count: {dup['duplicate_count']}")
            print(f"     IDs: {dup['product_ids']}")
            print(f"     External IDs: {dup['external_ids']}")
            print()
        conn.close()
        return False
    else:
        print("✅ No duplicate products found in database")
        conn.close()
        return True

if __name__ == "__main__":
    print("🔧 Validating Import Logic Patch")
    print("=" * 35)
    
    # Test the patched method
    test_success = test_ensure_product_scenarios()
    
    # Validate database state
    db_clean = validate_no_duplicates_in_db()
    
    if test_success and db_clean:
        print("\n🎉 VALIDATION SUCCESSFUL!")
        print("✅ The import logic patch is working correctly")
        print("✅ No duplicates detected in database")
        print("\n🚀 The system is ready for production use!")
    else:
        print("\n❌ VALIDATION FAILED!")
        if not test_success:
            print("❌ Import logic tests failed")
        if not db_clean:
            print("❌ Database still contains duplicates")
        print("\n🔧 Manual investigation required.")
