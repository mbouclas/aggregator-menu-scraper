#!/usr/bin/env python3
"""
Cleanup corrupted Caffè Nero data from database.
Same issue as Coffee Island - old imports created individual product names as categories.
"""
import sys
import os

# Add database directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

import psycopg2
from dotenv import load_dotenv

def cleanup_caffe_nero():
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
        
        # Get Caffè Nero restaurant IDs
        cursor.execute("SELECT id, name FROM restaurants WHERE name ILIKE '%nero%';")
        nero_restaurants = cursor.fetchall()
        
        if not nero_restaurants:
            print("No Caffè Nero restaurants found!")
            return
            
        for restaurant_id, restaurant_name in nero_restaurants:
            print(f"=== Cleaning up {restaurant_name} ===")
            
            # Check current state
            cursor.execute("SELECT COUNT(*) FROM products p JOIN categories c ON p.category_id = c.id WHERE c.restaurant_id = %s;", (restaurant_id,))
            current_products = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM categories WHERE restaurant_id = %s;", (restaurant_id,))
            current_categories = cursor.fetchone()[0]
            
            print(f"Current {restaurant_name} data: {current_products} products, {current_categories} categories")
            
            if current_products == 0 and current_categories == 0:
                print(f"No data found for {restaurant_name}")
                continue
                
            # Delete all products first (due to foreign key constraints)
            cursor.execute("""
                DELETE FROM product_prices 
                WHERE product_id IN (
                    SELECT p.id FROM products p 
                    JOIN categories c ON p.category_id = c.id 
                    WHERE c.restaurant_id = %s
                );
            """, (restaurant_id,))
            deleted_prices = cursor.rowcount
            print(f"Deleted {deleted_prices} product prices")
            
            cursor.execute("""
                DELETE FROM products 
                WHERE category_id IN (
                    SELECT id FROM categories WHERE restaurant_id = %s
                );
            """, (restaurant_id,))
            deleted_products = cursor.rowcount
            print(f"Deleted {deleted_products} products")
            
            # Delete all categories
            cursor.execute("DELETE FROM categories WHERE restaurant_id = %s;", (restaurant_id,))
            deleted_categories = cursor.rowcount
            print(f"Deleted {deleted_categories} categories")
            
            print(f"{restaurant_name} data cleanup completed successfully")
            print()
        
        # Commit the changes
        conn.commit()
        print("All Caffè Nero cleanup operations committed to database")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        if conn:
            conn.rollback()
        return False

if __name__ == "__main__":
    print("This will delete ALL Caffè Nero data from the database.")
    print("This includes products, categories, and prices for Caffè Nero restaurants.")
    print("You can re-import the data afterwards with the corrected scraper output.")
    print()
    
    confirm = input("Are you sure you want to proceed? (yes/no): ")
    if confirm.lower() == 'yes':
        success = cleanup_caffe_nero()
        if success:
            print("\n✅ Cleanup completed successfully!")
            print("You can now re-import Caffè Nero data with:")
            print("  python database/import_data.py --file output/foody_caffè-nero.json")
        else:
            print("\n❌ Cleanup failed!")
    else:
        print("Cleanup cancelled.")
