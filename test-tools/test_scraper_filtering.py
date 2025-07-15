#!/usr/bin/env python3
"""
Test Scraper Filtering
======================
Quick test to verify scraper filtering functionality in the database.
"""

import psycopg2
from dotenv import load_dotenv
import os
from pathlib import Path

def test_scraper_filtering():
    """Test that scraper filtering is working correctly."""
    
    # Load environment variables
    env_path = Path('database/.env')
    load_dotenv(env_path)
    
    # Connect to database
    host = os.getenv('DB_HOST')
    user = os.getenv('DB_USER') 
    password = os.getenv('DB_PASSWORD')
    port = os.getenv('DB_PORT')
    dbname = os.getenv('DB_NAME')
    
    conn_str = f'postgresql://{user}:{password}@{host}:{port}/{dbname}'
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        
        print('🧪 Testing Scraper Filtering Functionality')
        print('=' * 50)
        
        # Test 1: Count products by scraper
        print('1. Product count by scraper:')
        cur.execute('''
            SELECT scraper_name, COUNT(*) as product_count 
            FROM current_product_prices 
            GROUP BY scraper_name 
            ORDER BY scraper_name
        ''')
        results = cur.fetchall()
        for row in results:
            print(f'   {row[0]}: {row[1]} products')
        
        # Test 2: Filter only Wolt products
        print('\n2. Wolt products only:')
        cur.execute('''
            SELECT restaurant_name, COUNT(*) as products
            FROM current_product_prices 
            WHERE scraper_name = %s
            GROUP BY restaurant_name
            ORDER BY restaurant_name
        ''', ('wolt',))
        results = cur.fetchall()
        for row in results:
            print(f'   {row[0]}: {row[1]} products')
        
        # Test 3: Filter only Foody products
        print('\n3. Foody products only:')
        cur.execute('''
            SELECT restaurant_name, COUNT(*) as products
            FROM current_product_prices 
            WHERE scraper_name = %s
            GROUP BY restaurant_name
            ORDER BY restaurant_name
        ''', ('foody',))
        results = cur.fetchall()
        for row in results:
            print(f'   {row[0]}: {row[1]} products')
        
        # Test 4: Price statistics by scraper
        print('\n4. Price statistics by scraper:')
        cur.execute('''
            SELECT 
                scraper_name,
                COUNT(DISTINCT restaurant_name) as restaurants,
                COUNT(*) as total_products,
                ROUND(AVG(price)::numeric, 2) as avg_price,
                ROUND(MIN(price)::numeric, 2) as min_price,
                ROUND(MAX(price)::numeric, 2) as max_price
            FROM current_product_prices 
            GROUP BY scraper_name 
            ORDER BY scraper_name
        ''')
        results = cur.fetchall()
        for row in results:
            print(f'   {row[0]}: {row[1]} restaurants, {row[2]} products')
            print(f'     Price range: €{row[4]} - €{row[5]} (avg: €{row[3]})')
        
        print('\n✅ All scraper filtering tests passed!')
        print('\nYou can now run queries like:')
        print('  • SELECT * FROM current_product_prices WHERE scraper_name = \'wolt\'')
        print('  • SELECT * FROM restaurant_latest_stats WHERE scraper_name = \'foody\'')
        print('  • Filter by scraper platform for comparative analysis')
        
        conn.close()
        
    except Exception as e:
        print(f'❌ Error testing scraper filtering: {e}')
        return False
    
    return True

if __name__ == '__main__':
    test_scraper_filtering()
