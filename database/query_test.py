#!/usr/bin/env python3
"""
Quick Database Query Tool
========================
Run sample queries against the scraper database to verify data.
"""

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os
from pathlib import Path

def load_db_config():
    """Load database configuration from .env file."""
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
    
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'scraper_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '')
    }

def run_query(query, description):
    """Run a query and display results."""
    config = load_db_config()
    
    try:
        conn = psycopg2.connect(**config)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query)
            results = cur.fetchall()
            
            print(f"\n{'='*60}")
            print(f"📊 {description}")
            print(f"{'='*60}")
            
            if not results:
                print("No results found.")
                return
            
            # Print column headers
            if results:
                headers = list(results[0].keys())
                print(" | ".join(f"{h:15}" for h in headers))
                print("-" * (len(headers) * 18))
                
                # Print first 10 rows
                for i, row in enumerate(results[:10]):
                    print(" | ".join(f"{str(row[h])[:15]:15}" for h in headers))
                
                if len(results) > 10:
                    print(f"... and {len(results) - 10} more rows")
                    
                print(f"\nTotal: {len(results)} rows")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Run sample queries."""
    print("🔍 Querying Scraper Database")
    print("=" * 40)
    
    # Query 1: Restaurant summary
    run_query("""
        SELECT 
            restaurant_name,
            domain_name,
            total_products,
            total_categories,
            scraped_at::date
        FROM restaurant_latest_stats
        ORDER BY restaurant_name, domain_name
    """, "Restaurant Summary")
    
    # Query 2: Products with discounts
    run_query("""
        SELECT 
            restaurant_name,
            product_name,
            category_name,
            original_price,
            price,
            discount_percentage
        FROM current_product_prices 
        WHERE discount_percentage > 0
        ORDER BY discount_percentage DESC
        LIMIT 10
    """, "Top 10 Products with Discounts")
    
    # Query 3: Price comparison across restaurants
    run_query("""
        SELECT 
            product_name,
            restaurant_name,
            price,
            currency
        FROM current_product_prices 
        WHERE product_name ILIKE '%chicken%'
        ORDER BY product_name, price
    """, "Chicken Products Price Comparison")
    
    # Query 4: Category breakdown
    run_query("""
        SELECT 
            restaurant_name,
            category_name,
            COUNT(*) as product_count,
            ROUND(AVG(price)::numeric, 2) as avg_price,
            COUNT(*) FILTER (WHERE discount_percentage > 0) as discounted_count
        FROM current_product_prices
        GROUP BY restaurant_name, category_name
        ORDER BY restaurant_name, product_count DESC
    """, "Category Breakdown by Restaurant")
    
    # Query 5: Database statistics
    run_query("""
        SELECT 
            'Restaurants' as table_name, COUNT(*) as count FROM restaurants
        UNION ALL
        SELECT 'Products', COUNT(*) FROM products
        UNION ALL
        SELECT 'Price Records', COUNT(*) FROM product_prices
        UNION ALL
        SELECT 'Categories', COUNT(*) FROM categories
        UNION ALL
        SELECT 'Sessions', COUNT(*) FROM scraping_sessions
    """, "Database Statistics")

if __name__ == '__main__':
    main()
