#!/usr/bin/env python3
"""
Final cleanup script to remove any remaining "Uncategorized" products.
This will identify and remove products that are still categorized as "Uncategorized"
after the bulk import process.
"""
import sys
import os

# Add database directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))

import psycopg2
from dotenv import load_dotenv

def final_uncategorized_cleanup():
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
        
        print("=== Final Cleanup: Remove All 'Uncategorized' Products ===\n")
        
        # Find all restaurants with "Uncategorized" products
        cursor.execute("""
            SELECT r.id, r.name, COUNT(p.id) as uncategorized_count
            FROM restaurants r
            JOIN categories c ON r.id = c.restaurant_id
            JOIN products p ON c.id = p.category_id
            WHERE c.name = 'Uncategorized'
            GROUP BY r.id, r.name
            ORDER BY uncategorized_count DESC;
        """)
        
        restaurants_with_uncategorized = cursor.fetchall()
        
        if not restaurants_with_uncategorized:
            print("✅ No restaurants have 'Uncategorized' products!")
            return True
            
        print(f"Found {len(restaurants_with_uncategorized)} restaurants with 'Uncategorized' products:")
        total_uncategorized = 0
        for restaurant_id, restaurant_name, count in restaurants_with_uncategorized:
            print(f"  - {restaurant_name}: {count} uncategorized products")
            total_uncategorized += count
            
        print(f"\nTotal 'Uncategorized' products to remove: {total_uncategorized}")
        print()
        
        confirm = input("Remove all 'Uncategorized' products? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cleanup cancelled.")
            return False
            
        # Remove all uncategorized products
        deleted_prices = 0
        deleted_products = 0
        deleted_categories = 0
        
        for restaurant_id, restaurant_name, count in restaurants_with_uncategorized:
            print(f"Cleaning {restaurant_name}...")
            
            # Delete product prices first
            cursor.execute("""
                DELETE FROM product_prices 
                WHERE product_id IN (
                    SELECT p.id FROM products p 
                    JOIN categories c ON p.category_id = c.id 
                    WHERE c.restaurant_id = %s AND c.name = 'Uncategorized'
                );
            """, (restaurant_id,))
            prices_deleted = cursor.rowcount
            deleted_prices += prices_deleted
            
            # Delete products
            cursor.execute("""
                DELETE FROM products 
                WHERE category_id IN (
                    SELECT id FROM categories 
                    WHERE restaurant_id = %s AND name = 'Uncategorized'
                );
            """, (restaurant_id,))
            products_deleted = cursor.rowcount
            deleted_products += products_deleted
            
            # Delete "Uncategorized" categories
            cursor.execute("""
                DELETE FROM categories 
                WHERE restaurant_id = %s AND name = 'Uncategorized';
            """, (restaurant_id,))
            categories_deleted = cursor.rowcount
            deleted_categories += categories_deleted
            
            print(f"  Deleted {prices_deleted} prices, {products_deleted} products, {categories_deleted} categories")
        
        # Commit changes
        conn.commit()
        
        print(f"\n=== Final Cleanup Summary ===")
        print(f"Total product prices deleted: {deleted_prices}")
        print(f"Total products deleted: {deleted_products}")
        print(f"Total 'Uncategorized' categories deleted: {deleted_categories}")
        print(f"Restaurants cleaned: {len(restaurants_with_uncategorized)}")
        
        print("\n✅ Final cleanup completed successfully!")
        print("All restaurants should now have only proper categories.")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error during final cleanup: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False

if __name__ == "__main__":
    print("This will remove ALL products that are categorized as 'Uncategorized'")
    print("from ALL restaurants in the database.")
    print("This is a final cleanup step to ensure all remaining products have proper categories.")
    print()
    
    success = final_uncategorized_cleanup()
    if success:
        print("\n🎉 All 'Uncategorized' products have been removed!")
        print("You can now run queries and get only properly categorized products.")
    else:
        print("\n❌ Final cleanup failed or was cancelled.")
