#!/usr/bin/env python3
"""
Check all restaurants for category corruption and identify which ones need fixing.
This script will identify restaurants with the corruption pattern where individual
product names became categories instead of proper menu categories.
"""
import sys
import os

# Add database directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))

import psycopg2
from dotenv import load_dotenv

def check_all_restaurants():
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
        
        print("=== Checking All Restaurants for Category Corruption ===\n")
        
        # Get all restaurants
        cursor.execute("SELECT id, name FROM restaurants ORDER BY name;")
        restaurants = cursor.fetchall()
        
        corrupted_restaurants = []
        
        for restaurant_id, restaurant_name in restaurants:
            # Check categories vs products ratio - corruption indicator
            cursor.execute("SELECT COUNT(*) FROM categories WHERE restaurant_id = %s;", (restaurant_id,))
            category_count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) 
                FROM products p 
                JOIN categories c ON p.category_id = c.id 
                WHERE c.restaurant_id = %s;
            """, (restaurant_id,))
            product_count = cursor.fetchone()[0]
            
            if category_count > 0 and product_count > 0:
                ratio = category_count / product_count
                
                print(f"{restaurant_name}:")
                print(f"  Categories: {category_count}, Products: {product_count}, Ratio: {ratio:.2f}")
                
                # If we have more than 50% categories to products, it's likely corrupted
                # Normal restaurants should have 5-30 categories for 50-300 products
                if ratio > 0.5 or category_count > 50:
                    print(f"  ⚠️  SUSPICIOUS - Likely corrupted!")
                    corrupted_restaurants.append((restaurant_id, restaurant_name, category_count, product_count))
                    
                    # Sample some category names to confirm corruption
                    cursor.execute("""
                        SELECT name FROM categories 
                        WHERE restaurant_id = %s 
                        ORDER BY name 
                        LIMIT 5;
                    """, (restaurant_id,))
                    sample_categories = cursor.fetchall()
                    print(f"  Sample categories: {[cat[0] for cat in sample_categories]}")
                else:
                    print(f"  ✅ Looks healthy")
                    
                print()
            elif category_count == 0 and product_count == 0:
                print(f"{restaurant_name}: No data")
            else:
                print(f"{restaurant_name}: Partial data (cats: {category_count}, prods: {product_count})")
        
        print("\n=== Summary ===")
        print(f"Total restaurants: {len(restaurants)}")
        print(f"Corrupted restaurants: {len(corrupted_restaurants)}")
        
        if corrupted_restaurants:
            print("\nRestaurants needing cleanup:")
            for _, name, cats, prods in corrupted_restaurants:
                print(f"  - {name} ({cats} categories, {prods} products)")
        
        cursor.close()
        conn.close()
        
        return corrupted_restaurants
        
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    check_all_restaurants()
