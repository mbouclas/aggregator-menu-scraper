#!/usr/bin/env python3
"""
Verify that Coffee Island products are now properly categorized after the fix.
"""
import sys
import os

# Add database directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

import psycopg2
from dotenv import load_dotenv

def main():
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
        
        print("=== Coffee Island Category Verification ===\n")
        
        # Check total categories for Coffee Island
        cursor.execute('''
            SELECT COUNT(*) 
            FROM categories c
            JOIN restaurants r ON c.restaurant_id = r.id
            WHERE r.name = 'Coffee Island';
        ''')
        total_categories = cursor.fetchone()[0]
        print(f"Total categories: {total_categories}")
        
        # Check total products for Coffee Island
        cursor.execute('''
            SELECT COUNT(*) 
            FROM products p
            JOIN categories c ON p.category_id = c.id
            JOIN restaurants r ON c.restaurant_id = r.id
            WHERE r.name = 'Coffee Island';
        ''')
        total_products = cursor.fetchone()[0]
        print(f"Total products: {total_products}")
        
        print(f"\n=== Categories and Product Counts ===")
        
        # Get all categories with product counts
        cursor.execute('''
            SELECT 
                c.name as category_name,
                COUNT(p.id) as product_count
            FROM categories c
            LEFT JOIN products p ON c.id = p.category_id
            JOIN restaurants r ON c.restaurant_id = r.id
            WHERE r.name = 'Coffee Island'
            GROUP BY c.id, c.name
            ORDER BY product_count DESC, c.name;
        ''')
        
        categories = cursor.fetchall()
        for category_name, product_count in categories:
            print(f"  {category_name}: {product_count} products")
        
        print(f"\n=== Sample Products with Categories ===")
        
        # Show sample products from different categories
        cursor.execute('''
            SELECT 
                p.name as product_name,
                c.name as category_name,
                cpp.price
            FROM current_product_prices cpp
            JOIN products p ON cpp.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            JOIN restaurants r ON c.restaurant_id = r.id
            WHERE r.name = 'Coffee Island'
            ORDER BY c.name, p.name
            LIMIT 15;
        ''')
        
        products = cursor.fetchall()
        for product_name, category_name, price in products:
            print(f"  {category_name}: {product_name} - €{price:.2f}")
        
        # Check if any products are still "Uncategorized"
        cursor.execute('''
            SELECT COUNT(*) 
            FROM products p
            JOIN categories c ON p.category_id = c.id
            JOIN restaurants r ON c.restaurant_id = r.id
            WHERE r.name = 'Coffee Island' AND c.name = 'Uncategorized';
        ''')
        uncategorized_count = cursor.fetchone()[0]
        
        print(f"\n=== Fix Verification ===")
        print(f"Products with 'Uncategorized' category: {uncategorized_count}")
        
        if uncategorized_count == 0:
            print("✅ SUCCESS: No products are 'Uncategorized' - the fix worked!")
        else:
            print("❌ ISSUE: Some products are still 'Uncategorized'")
        
        # Show category diversity
        non_empty_categories = len([c for c in categories if c[1] > 0])
        print(f"Categories with products: {non_empty_categories}")
        print(f"Expected categories (from scraper): ~27-28")
        
        if non_empty_categories >= 25:
            print("✅ SUCCESS: Good category diversity achieved!")
        else:
            print("⚠️  WARNING: Expected more categories")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
