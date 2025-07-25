#!/usr/bin/env python3
"""
Test the original user query that was showing Uncategorized products.
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

conn_str = load_db_config()
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

print('=== ORIGINAL USER QUERY TEST ===')
print('Testing queries that were showing "Uncategorized" before...')

# Test the query that would have shown "Uncategorized" products for Second Cup
cur.execute("""
    SELECT 
        c.name as category_name,
        p.name as product_name,
        pp.price
    FROM restaurants r
    JOIN categories c ON r.id = c.restaurant_id
    JOIN products p ON c.id = p.category_id
    JOIN product_prices pp ON p.id = pp.product_id
    WHERE r.name LIKE '%Second Cup%' 
    AND r.name NOT LIKE '%Recanto%'
    ORDER BY c.name, p.name
    LIMIT 20
""")

results = cur.fetchall()
print(f'\nSecond Cup products (first 20):')
for category, product, price in results:
    print(f'  {category}: {product} - €{price}')

# Check if any "Uncategorized" products exist anywhere
print('\n=== CHECKING ALL UNCATEGORIZED PRODUCTS ===')
cur.execute("""
    SELECT 
        r.name as restaurant_name,
        c.name as category_name,
        p.name as product_name,
        pp.price
    FROM restaurants r
    JOIN categories c ON r.id = c.restaurant_id
    JOIN products p ON c.id = p.category_id
    JOIN product_prices pp ON p.id = pp.product_id
    WHERE c.name ILIKE '%uncategorized%'
    ORDER BY r.name, p.name
""")

uncategorized_products = cur.fetchall()
if uncategorized_products:
    print(f'Found {len(uncategorized_products)} Uncategorized products:')
    for restaurant, category, product, price in uncategorized_products:
        print(f'  {restaurant}: {category} - {product} (€{price})')
else:
    print('✅ NO UNCATEGORIZED PRODUCTS FOUND! The issue is completely fixed!')

conn.close()
