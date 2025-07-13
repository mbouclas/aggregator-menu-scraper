#!/usr/bin/env python3
"""
Test query to check offer_name data in the database.
"""

import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

def load_db_config() -> str:
    """Load database configuration from .env file."""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url
    
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'scraper_db')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    if db_password:
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        return f"postgresql://{db_user}@{db_host}:{db_port}/{db_name}"

def main():
    """Query offer_name data from the database."""
    connection_string = load_db_config()
    
    try:
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()
        
        print("🔍 Checking offer_name data in database")
        print("=" * 60)
        
        # Check for records with non-empty offer_name
        cur.execute("""
            SELECT 
                r.name as restaurant_name,
                p.name as product_name,
                pp.offer_name,
                pp.price,
                pp.scraped_at
            FROM product_prices pp
            JOIN products p ON pp.product_id = p.id
            JOIN restaurants r ON p.restaurant_id = r.id
            WHERE pp.offer_name IS NOT NULL 
            AND pp.offer_name != ''
            ORDER BY pp.scraped_at DESC
            LIMIT 10;
        """)
        
        results = cur.fetchall()
        
        if results:
            print(f"Found {len(results)} products with offer_name:")
            print("-" * 60)
            for row in results:
                restaurant, product, offer, price, scraped = row
                print(f"Restaurant: {restaurant}")
                print(f"Product: {product}")
                print(f"Offer: {offer}")
                print(f"Price: €{price}")
                print(f"Scraped: {scraped}")
                print("-" * 60)
        else:
            print("❌ No products found with offer_name data")
            
            # Check if there are any price records at all
            cur.execute("SELECT COUNT(*) FROM product_prices;")
            total_prices = cur.fetchone()[0]
            print(f"Total price records: {total_prices}")
            
            # Check if offer_name column exists and what values it has
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(offer_name) as not_null,
                    COUNT(CASE WHEN offer_name != '' THEN 1 END) as not_empty
                FROM product_prices;
            """)
            stats = cur.fetchone()
            print(f"Offer_name stats - Total: {stats[0]}, Not NULL: {stats[1]}, Not empty: {stats[2]}")
            
            # Show some sample data
            cur.execute("""
                SELECT 
                    r.name as restaurant_name,
                    p.name as product_name,
                    pp.offer_name,
                    pp.scraped_at
                FROM product_prices pp
                JOIN products p ON pp.product_id = p.id
                JOIN restaurants r ON p.restaurant_id = r.id
                WHERE r.name LIKE '%KFC%'
                ORDER BY pp.scraped_at DESC
                LIMIT 5;
            """)
            
            sample_results = cur.fetchall()
            print("\nSample KFC data:")
            for row in sample_results:
                restaurant, product, offer, scraped = row
                print(f"  {restaurant} - {product} - offer_name: '{offer}' - {scraped}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
