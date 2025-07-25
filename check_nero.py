#!/usr/bin/env python3
"""
Check Caffè Nero data in database
"""
import sys
import os

# Add database directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

import psycopg2
from dotenv import load_dotenv

def check_nero():
    # Load environment variables from database/.env
    env_path = os.path.join(os.path.dirname(__file__), 'database', '.env')
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
        
        print("=== Restaurant Check ===")
        
        # Check what restaurants we have
        cursor.execute("SELECT name FROM restaurants ORDER BY name;")
        restaurants = cursor.fetchall()
        print('Available restaurants:')
        for r in restaurants:
            print(f'  {r[0]}')

        print()

        # Check Caffè Nero specifically
        cursor.execute("SELECT id, name FROM restaurants WHERE name ILIKE '%nero%';")
        nero_restaurants = cursor.fetchall()
        print('Nero restaurants found:')
        for r in nero_restaurants:
            print(f'  ID: {r[0]}, Name: {r[1]}')

        if nero_restaurants:
            restaurant_id = nero_restaurants[0][0]
            restaurant_name = nero_restaurants[0][1]
            
            print(f"\n=== Analysis for {restaurant_name} ===")
            
            # Check categories for Caffè Nero
            cursor.execute("SELECT COUNT(*) FROM categories WHERE restaurant_id = %s;", (restaurant_id,))
            cat_count = cursor.fetchone()[0]
            print(f'Total categories: {cat_count}')
            
            # Check products for Caffè Nero  
            cursor.execute("SELECT COUNT(*) FROM products p JOIN categories c ON p.category_id = c.id WHERE c.restaurant_id = %s;", (restaurant_id,))
            prod_count = cursor.fetchone()[0]
            print(f'Total products: {prod_count}')
            
            # Check categories
            cursor.execute("SELECT name, COUNT(p.id) as product_count FROM categories c LEFT JOIN products p ON c.id = p.category_id WHERE c.restaurant_id = %s GROUP BY c.id, c.name ORDER BY product_count DESC, c.name;", (restaurant_id,))
            categories = cursor.fetchall()
            print('Categories with product counts:')
            for name, count in categories:
                print(f'  {name}: {count} products')
                
            # Sample some products
            print(f"\n=== Sample Products ===")
            cursor.execute("""
                SELECT p.name as product_name, c.name as category_name, cpp.price 
                FROM current_product_prices cpp 
                JOIN products p ON cpp.product_id = p.id 
                JOIN categories c ON p.category_id = c.id 
                JOIN restaurants r ON c.restaurant_id = r.id 
                WHERE r.name ILIKE '%nero%' 
                ORDER BY cpp.price DESC 
                LIMIT 10
            """)
            products = cursor.fetchall()
            for product_name, category_name, price in products:
                print(f'  {category_name}: {product_name} - €{price:.2f}')
        else:
            print("No Caffè Nero restaurants found!")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_nero()
