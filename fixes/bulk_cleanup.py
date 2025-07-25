#!/usr/bin/env python3
"""
Universal cleanup script to fix category corruption for all restaurants.
This script will:
1. Clean up corrupted restaurant data
2. Re-import from correct scraper output files if they exist
"""
import sys
import os
import glob

# Add database directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))

import psycopg2
from dotenv import load_dotenv

def cleanup_restaurant(cursor, restaurant_id, restaurant_name):
    """Clean up all data for a specific restaurant"""
    print(f"=== Cleaning up {restaurant_name} ===")
    
    # Check current state
    cursor.execute("""
        SELECT COUNT(*) 
        FROM products p 
        JOIN categories c ON p.category_id = c.id 
        WHERE c.restaurant_id = %s;
    """, (restaurant_id,))
    current_products = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM categories WHERE restaurant_id = %s;", (restaurant_id,))
    current_categories = cursor.fetchone()[0]
    
    print(f"Current {restaurant_name} data: {current_products} products, {current_categories} categories")
    
    if current_products == 0 and current_categories == 0:
        print(f"No data found for {restaurant_name}")
        return 0, 0, 0
        
    # Delete all product prices first (due to foreign key constraints)
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
    
    # Delete all products
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
    return deleted_prices, deleted_products, deleted_categories

def find_output_file(restaurant_name):
    """Find corresponding output file for a restaurant"""
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    
    # Normalize restaurant name for file matching
    normalized_name = restaurant_name.lower()
    normalized_name = normalized_name.replace('café', 'caffe')
    normalized_name = normalized_name.replace('caffè', 'caffe')
    normalized_name = normalized_name.replace(' ', '-')
    normalized_name = normalized_name.replace("'", '')
    normalized_name = normalized_name.replace(".", '')
    
    # Common patterns for file names
    patterns = [
        f"*{normalized_name}*.json",
        f"*{normalized_name.replace('-', '_')}*.json",
        f"*{normalized_name.replace('-', '')}*.json"
    ]
    
    for pattern in patterns:
        files = glob.glob(os.path.join(output_dir, pattern))
        if files:
            return files[0]
    
    # Try more specific patterns
    specific_mappings = {
        'bean-bar': '*bean-bar*.json',
        'coffeehouse': '*coffeehouse*.json',
        'costa-coffee': '*costa-coffee*.json',
        'gloria-jeans-coffees': '*gloria-jean*.json',
        'kawacoms-ipanema-espresso': '*kawacoms*.json',
        'mikel-coffee-company': '*mikel*.json',
        'overoll-croissanterie': '*overoll*.json',
        'pasta-strada': '*pasta-strada*.json',
        'red-sheep-coffee-co-engomi': '*red-sheep-coffee-co-engomi*.json',
        'second-cup': '*second-cup*.json',
        'starbucks': '*starbucks*.json'
    }
    
    if normalized_name in specific_mappings:
        files = glob.glob(os.path.join(output_dir, specific_mappings[normalized_name]))
        if files:
            return files[0]
    
    return None

def bulk_cleanup_and_reimport():
    """Clean up all corrupted restaurants and re-import if output files exist"""
    
    # Corrupted restaurants identified from the check
    corrupted_restaurants = [
        'Bean Bar',
        'COFFEEHOUSE', 
        'Costa Coffee',
        'Gloria Jean\'s Coffees',
        'Kawacom\'s Ipanema Espresso',
        'Mikel Coffee Company',
        'Overoll Croissanterie',
        'Pasta Strada',
        'Red Sheep Coffee Co. Engomi',
        'Second Cup',
        'Starbucks'
    ]
    
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
        
        print("=== Bulk Cleanup and Re-import Process ===\n")
        
        cleanup_summary = []
        reimport_summary = []
        
        for restaurant_name in corrupted_restaurants:
            # Get restaurant ID
            cursor.execute("SELECT id FROM restaurants WHERE name = %s;", (restaurant_name,))
            result = cursor.fetchone()
            
            if not result:
                print(f"❌ Restaurant '{restaurant_name}' not found in database")
                continue
                
            restaurant_id = result[0]
            
            # Cleanup
            deleted_prices, deleted_products, deleted_categories = cleanup_restaurant(
                cursor, restaurant_id, restaurant_name
            )
            cleanup_summary.append((restaurant_name, deleted_products, deleted_categories))
            
            # Find corresponding output file
            output_file = find_output_file(restaurant_name)
            
            if output_file:
                print(f"✅ Found output file: {os.path.basename(output_file)}")
                reimport_summary.append((restaurant_name, output_file))
            else:
                print(f"⚠️  No output file found for {restaurant_name}")
            
            print()
        
        # Commit cleanup changes
        conn.commit()
        print("All cleanup operations committed to database\n")
        
        # Summary
        print("=== Cleanup Summary ===")
        total_products = sum(prods for _, prods, _ in cleanup_summary)
        total_categories = sum(cats for _, _, cats in cleanup_summary)
        print(f"Total products deleted: {total_products}")
        print(f"Total categories deleted: {total_categories}")
        print(f"Restaurants cleaned: {len(cleanup_summary)}")
        
        print("\n=== Re-import Files Available ===")
        for restaurant_name, output_file in reimport_summary:
            print(f"  {restaurant_name}: {os.path.basename(output_file)}")
        
        print(f"\nFound {len(reimport_summary)} output files for re-import")
        
        cursor.close()
        conn.close()
        
        return reimport_summary
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        if 'conn' in locals():
            conn.rollback()
        return []

if __name__ == "__main__":
    print("This will delete ALL data for the following corrupted restaurants:")
    print("- Bean Bar")
    print("- COFFEEHOUSE") 
    print("- Costa Coffee")
    print("- Gloria Jean's Coffees")
    print("- Kawacom's Ipanema Espresso")
    print("- Mikel Coffee Company")
    print("- Overoll Croissanterie")
    print("- Pasta Strada")
    print("- Red Sheep Coffee Co. Engomi")
    print("- Second Cup")
    print("- Starbucks")
    print()
    print("This includes products, categories, and prices for these restaurants.")
    print("Available output files will be identified for re-import.")
    print()
    
    confirm = input("Are you sure you want to proceed with bulk cleanup? (yes/no): ")
    if confirm.lower() == 'yes':
        reimport_files = bulk_cleanup_and_reimport()
        if reimport_files:
            print(f"\n✅ Cleanup completed successfully!")
            print(f"Found {len(reimport_files)} files ready for re-import.")
            print("You can re-import them using the re-import script.")
        else:
            print("\n❌ Cleanup failed!")
    else:
        print("Cleanup cancelled.")
