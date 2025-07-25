#!/usr/bin/env python3
"""
Script to validate Second Cup import and check for Uncategorized categories.
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

# Check the Second Cup restaurant and its categories
print('=== SECOND CUP RESTAURANT CHECK ===')
cur.execute("""
    SELECT r.name, r.id 
    FROM restaurants r 
    WHERE r.name LIKE '%Second Cup%'
    ORDER BY r.name
""")
restaurants = cur.fetchall()
for name, rest_id in restaurants:
    print(f'Restaurant: {name} (ID: {rest_id})')

print('\n=== CATEGORIES FOR SECOND CUP ===')
if restaurants:
    rest_id = restaurants[0][1]
    cur.execute("""
        SELECT c.name, COUNT(p.id) as product_count
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id
        WHERE c.restaurant_id = %s
        GROUP BY c.id, c.name
        ORDER BY c.name
    """, (rest_id,))
    categories = cur.fetchall()
    for cat_name, prod_count in categories:
        print(f'  {cat_name}: {prod_count} products')

print('\n=== CHECKING FOR UNCATEGORIZED ===')
cur.execute("""
    SELECT c.name, r.name, COUNT(p.id) as product_count
    FROM categories c
    JOIN restaurants r ON c.restaurant_id = r.id
    LEFT JOIN products p ON c.id = p.category_id
    WHERE c.name ILIKE '%uncategorized%'
    GROUP BY c.id, c.name, r.name
    ORDER BY r.name, c.name
""")
uncategorized = cur.fetchall()
if uncategorized:
    for cat_name, rest_name, prod_count in uncategorized:
        print(f'  {rest_name}: {cat_name} ({prod_count} products)')
else:
    print('  ✅ No Uncategorized categories found!')

print('\n=== SAMPLE PRODUCTS FROM SECOND CUP ===')
if restaurants:
    rest_id = restaurants[0][1]
    cur.execute("""
        SELECT p.name, c.name as category, pp.price
        FROM products p
        JOIN categories c ON p.category_id = c.id
        JOIN product_prices pp ON p.id = pp.product_id
        WHERE c.restaurant_id = %s
        ORDER BY c.name, p.name
        LIMIT 15
    """, (rest_id,))
    products = cur.fetchall()
    for prod_name, cat_name, price in products:
        print(f'  {cat_name}: {prod_name} - €{price}')

conn.close()
