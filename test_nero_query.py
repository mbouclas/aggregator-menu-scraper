#!/usr/bin/env python3
"""
Test the exact query the user provided to verify Caffè Nero fix
"""
import sys
import os

# Add database directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

import psycopg2
from dotenv import load_dotenv

def test_nero_query():
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
        
        print("=== Testing Your Exact Query ===")
        print("Query: SELECT p.name as product_name, c.name as category_name, cpp.price FROM current_product_prices cpp JOIN products p ON cpp.product_id = p.id JOIN categories c ON p.category_id = c.id JOIN restaurants r ON c.restaurant_id = r.id WHERE r.name ilike '%nero%' ORDER BY cpp.price DESC LIMIT 50")
        print()
        
        # Your exact query
        cursor.execute("""
            SELECT p.name as product_name, c.name as category_name, cpp.price 
            FROM current_product_prices cpp 
            JOIN products p ON cpp.product_id = p.id 
            JOIN categories c ON p.category_id = c.id 
            JOIN restaurants r ON c.restaurant_id = r.id 
            WHERE r.name ilike '%nero%' 
            ORDER BY cpp.price DESC 
            LIMIT 50
        """)

        products = cursor.fetchall()
        print(f'Found {len(products)} products:')
        print()
        
        # Show all results
        for i, (product_name, category_name, price) in enumerate(products, 1):
            print(f'{i:2d}. {category_name}: {product_name} - €{price:.2f}')
        
        print()
        
        # Check for any "Uncategorized"
        uncategorized_count = sum(1 for _, category_name, _ in products if category_name == 'Uncategorized')
        
        print(f"=== Fix Verification ===")
        print(f'Products with "Uncategorized" category: {uncategorized_count}')
        
        if uncategorized_count == 0:
            print('✅ SUCCESS: No more "Uncategorized" products for Caffè Nero!')
        else:
            print('❌ Still has uncategorized products')
            
        # Show unique categories
        unique_categories = set(category_name for _, category_name, _ in products)
        print(f'\nUnique categories found: {len(unique_categories)}')
        for cat in sorted(unique_categories):
            count = sum(1 for _, category_name, _ in products if category_name == cat)
            print(f'  {cat}: {count} products')
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_nero_query()
