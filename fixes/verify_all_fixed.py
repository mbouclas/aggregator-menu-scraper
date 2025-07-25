#!/usr/bin/env python3
"""
Verify that all restaurants now have proper categories after the bulk fix.
This script will test queries for all restaurants to ensure no "Uncategorized" issues remain.
"""
import sys
import os

# Add database directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))

import psycopg2
from dotenv import load_dotenv

def verify_all_restaurants():
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
        
        print("=== Verification: All Restaurants Category Fix ===\n")
        
        # Get all restaurants
        cursor.execute("SELECT id, name FROM restaurants ORDER BY name;")
        restaurants = cursor.fetchall()
        
        fixed_restaurants = []
        still_has_uncategorized = []
        healthy_restaurants = []
        
        for restaurant_id, restaurant_name in restaurants:
            # Check for "Uncategorized" products
            cursor.execute("""
                SELECT COUNT(*) 
                FROM products p 
                JOIN categories c ON p.category_id = c.id 
                WHERE c.restaurant_id = %s AND c.name = 'Uncategorized';
            """, (restaurant_id,))
            uncategorized_count = cursor.fetchone()[0]
            
            # Get total products and categories
            cursor.execute("""
                SELECT COUNT(*) 
                FROM products p 
                JOIN categories c ON p.category_id = c.id 
                WHERE c.restaurant_id = %s;
            """, (restaurant_id,))
            total_products = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM categories WHERE restaurant_id = %s;", (restaurant_id,))
            total_categories = cursor.fetchone()[0]
            
            if total_products > 0:
                ratio = total_categories / total_products if total_products > 0 else 0
                
                print(f"{restaurant_name}:")
                print(f"  Products: {total_products}, Categories: {total_categories}, Ratio: {ratio:.2f}")
                
                if uncategorized_count > 0:
                    print(f"  ❌ Has {uncategorized_count} 'Uncategorized' products")
                    still_has_uncategorized.append((restaurant_name, uncategorized_count))
                elif ratio > 0.5:
                    print(f"  ⚠️  High category ratio - may still have corruption")
                else:
                    print(f"  ✅ Healthy categories")
                    healthy_restaurants.append(restaurant_name)
                    
                    # Sample a few categories to show quality
                    cursor.execute("""
                        SELECT c.name, COUNT(p.id) as product_count
                        FROM categories c 
                        LEFT JOIN products p ON c.id = p.category_id 
                        WHERE c.restaurant_id = %s AND p.id IS NOT NULL
                        GROUP BY c.id, c.name 
                        ORDER BY product_count DESC 
                        LIMIT 3;
                    """, (restaurant_id,))
                    sample_categories = cursor.fetchall()
                    if sample_categories:
                        print(f"  Top categories: {[f'{cat[0]} ({cat[1]})' for cat in sample_categories]}")
                
                print()
        
        print("=== Final Summary ===")
        print(f"Total restaurants: {len(restaurants)}")
        print(f"Restaurants with healthy categories: {len(healthy_restaurants)}")
        print(f"Restaurants still with 'Uncategorized': {len(still_has_uncategorized)}")
        
        if still_has_uncategorized:
            print("\nRestaurants still needing attention:")
            for name, count in still_has_uncategorized:
                print(f"  - {name} ({count} uncategorized products)")
        
        if len(healthy_restaurants) >= len(restaurants) - len(still_has_uncategorized):
            print("\n🎉 SUCCESS: Category fix applied successfully to most restaurants!")
        
        # Test a few queries for key restaurants
        print("\n=== Query Tests ===")
        test_restaurants = ['Caffè Nero', 'Coffee Island', 'Starbucks', 'Costa Coffee']
        
        for test_restaurant in test_restaurants:
            cursor.execute("""
                SELECT p.name as product_name, c.name as category_name, cpp.price 
                FROM current_product_prices cpp 
                JOIN products p ON cpp.product_id = p.id 
                JOIN categories c ON p.category_id = c.id 
                JOIN restaurants r ON c.restaurant_id = r.id 
                WHERE r.name = %s 
                ORDER BY cpp.price DESC 
                LIMIT 3
            """, (test_restaurant,))
            
            products = cursor.fetchall()
            if products:
                print(f"\n{test_restaurant} - Top 3 products:")
                for product_name, category_name, price in products:
                    print(f"  {category_name}: {product_name} - €{price:.2f}")
            else:
                print(f"\n{test_restaurant}: No products found")
        
        cursor.close()
        conn.close()
        
        return len(still_has_uncategorized) == 0
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = verify_all_restaurants()
    if success:
        print("\n✅ All restaurants verified successfully!")
    else:
        print("\n⚠️  Some restaurants may still need attention.")
