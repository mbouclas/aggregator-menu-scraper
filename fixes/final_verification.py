#!/usr/bin/env python3
"""
Final verification that the category fix is complete.
Test the original problematic queries to ensure they now work properly.
"""
import sys
import os

# Add database directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))

import psycopg2
from dotenv import load_dotenv

def test_original_queries():
    # Load environment variables from database/.env
    env_path = os.path.join(os.path.dirname(__file__), '..', 'database', '.env')
    load_dotenv(env_path)
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        
        cursor = conn.cursor()
        
        print("=== Final Verification: Testing Original Problematic Queries ===\n")
        
        # Test 1: Original Caffè Nero query
        print("🔍 Test 1: Original Caffè Nero query")
        print("Query: SELECT p.name as product_name, c.name as category_name, cpp.price FROM current_product_prices cpp JOIN products p ON cpp.product_id = p.id JOIN categories c ON p.category_id = c.id JOIN restaurants r ON c.restaurant_id = r.id WHERE r.name ilike '%nero%' ORDER BY cpp.price DESC LIMIT 10")
        
        cursor.execute("""
            SELECT p.name as product_name, c.name as category_name, cpp.price 
            FROM current_product_prices cpp 
            JOIN products p ON cpp.product_id = p.id 
            JOIN categories c ON p.category_id = c.id 
            JOIN restaurants r ON c.restaurant_id = r.id 
            WHERE r.name ilike '%nero%' 
            ORDER BY cpp.price DESC 
            LIMIT 10
        """)
        
        nero_products = cursor.fetchall()
        uncategorized_nero = sum(1 for _, cat, _ in nero_products if cat == 'Uncategorized')
        
        print(f"Results: {len(nero_products)} products found")
        print(f"'Uncategorized' products: {uncategorized_nero}")
        
        if uncategorized_nero == 0:
            print("✅ SUCCESS: No 'Uncategorized' products in Caffè Nero!")
        else:
            print("❌ FAIL: Still has 'Uncategorized' products")
            
        print("Sample results:")
        for i, (product_name, category_name, price) in enumerate(nero_products[:5], 1):
            print(f"  {i}. {category_name}: {product_name} - €{price:.2f}")
        
        print()
        
        # Test 2: Coffee Island query
        print("🔍 Test 2: Coffee Island verification")
        cursor.execute("""
            SELECT p.name as product_name, c.name as category_name, cpp.price 
            FROM current_product_prices cpp 
            JOIN products p ON cpp.product_id = p.id 
            JOIN categories c ON p.category_id = c.id 
            JOIN restaurants r ON c.restaurant_id = r.id 
            WHERE r.name ilike '%coffee island%' 
            ORDER BY cpp.price DESC 
            LIMIT 10
        """)
        
        island_products = cursor.fetchall()
        uncategorized_island = sum(1 for _, cat, _ in island_products if cat == 'Uncategorized')
        
        print(f"Results: {len(island_products)} products found")
        print(f"'Uncategorized' products: {uncategorized_island}")
        
        if uncategorized_island == 0:
            print("✅ SUCCESS: No 'Uncategorized' products in Coffee Island!")
        else:
            print("❌ FAIL: Still has 'Uncategorized' products")
            
        print("Sample results:")
        for i, (product_name, category_name, price) in enumerate(island_products[:5], 1):
            print(f"  {i}. {category_name}: {product_name} - €{price:.2f}")
        
        print()
        
        # Test 3: Global check for any remaining "Uncategorized"
        print("🔍 Test 3: Global check for any remaining 'Uncategorized' products")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM products p 
            JOIN categories c ON p.category_id = c.id 
            WHERE c.name = 'Uncategorized';
        """)
        
        total_uncategorized = cursor.fetchone()[0]
        print(f"Total 'Uncategorized' products in entire database: {total_uncategorized}")
        
        if total_uncategorized == 0:
            print("✅ SUCCESS: No 'Uncategorized' products anywhere!")
        else:
            print("❌ FAIL: Still has 'Uncategorized' products somewhere")
        
        print()
        
        # Test 4: Sample queries for other major restaurants
        print("🔍 Test 4: Sample queries for other major restaurants")
        test_restaurants = ['Starbucks', 'Costa Coffee', 'Gloria Jean', 'Mikel Coffee']
        
        for restaurant_pattern in test_restaurants:
            cursor.execute("""
                SELECT COUNT(p.id), COUNT(DISTINCT c.name) as category_count
                FROM products p 
                JOIN categories c ON p.category_id = c.id 
                JOIN restaurants r ON c.restaurant_id = r.id 
                WHERE r.name ilike %s;
            """, (f'%{restaurant_pattern}%',))
            
            result = cursor.fetchone()
            if result and result[0] > 0:
                product_count, category_count = result
                print(f"  {restaurant_pattern}: {product_count} products, {category_count} categories")
            else:
                print(f"  {restaurant_pattern}: No products found")
        
        print()
        
        # Final summary
        print("=== Final Verification Summary ===")
        
        cursor.execute("SELECT COUNT(*) FROM restaurants;")
        total_restaurants = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM products p 
            JOIN categories c ON p.category_id = c.id;
        """)
        total_products = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM categories;")
        total_categories = cursor.fetchone()[0]
        
        print(f"Database totals: {total_restaurants} restaurants, {total_products} products, {total_categories} categories")
        
        overall_success = (uncategorized_nero == 0 and uncategorized_island == 0 and total_uncategorized == 0)
        
        if overall_success:
            print("\n🎉 COMPLETE SUCCESS: All category issues have been fixed!")
            print("✅ Caffè Nero queries work properly")
            print("✅ Coffee Island queries work properly") 
            print("✅ No 'Uncategorized' products remain anywhere")
            print("\nYou can now run any restaurant query and get proper categories instead of 'Uncategorized'!")
        else:
            print("\n⚠️  Some issues may remain - check individual test results above")
        
        cursor.close()
        conn.close()
        
        return overall_success
        
    except Exception as e:
        print(f"Error during verification: {e}")
        return False

if __name__ == "__main__":
    test_original_queries()
