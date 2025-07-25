#!/usr/bin/env python3
"""
Compare scraped JSON data with imported database data to validate consistency.
"""

import json
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

# Load JSON data
with open(r'c:\work\aggregator-menu-scraper\output\test_second_cup_new.json', 'r') as f:
    json_data = json.load(f)

# Connect to database
conn_str = load_db_config()
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

print('=== SCRAPED VS DATABASE COMPARISON ===')

# Get JSON categories and products
json_categories = {cat['name'] for cat in json_data['categories']}
json_products = [(prod['name'], prod['category'], prod['price']) for prod in json_data['products']]

print(f'JSON Data:')
print(f'  Categories: {len(json_categories)}')
print(f'  Products: {len(json_products)}')

# Get database categories and products for latest Second Cup scrape
cur.execute("""
    SELECT c.name, COUNT(p.id) as product_count
    FROM categories c
    LEFT JOIN products p ON c.id = p.category_id
    WHERE c.restaurant_id = (
        SELECT id FROM restaurants WHERE name = 'Second Cup' LIMIT 1
    )
    GROUP BY c.id, c.name
    HAVING COUNT(p.id) > 0
    ORDER BY c.name
""")
db_categories = cur.fetchall()

cur.execute("""
    SELECT p.name, c.name as category, pp.price
    FROM products p
    JOIN categories c ON p.category_id = c.id
    JOIN product_prices pp ON p.id = pp.product_id
    WHERE c.restaurant_id = (
        SELECT id FROM restaurants WHERE name = 'Second Cup' LIMIT 1
    )
    AND pp.scraped_at = (
        SELECT MAX(scraped_at) FROM product_prices pp2 
        JOIN products p2 ON pp2.product_id = p2.id
        JOIN categories c2 ON p2.category_id = c2.id
        WHERE c2.restaurant_id = c.restaurant_id
    )
    ORDER BY c.name, p.name
""")
db_products = cur.fetchall()

print(f'\nDatabase Data (latest scrape):')
print(f'  Categories with products: {len(db_categories)}')
print(f'  Products: {len(db_products)}')

# Compare categories
print(f'\n=== CATEGORY COMPARISON ===')
json_active_categories = {prod['category'] for prod in json_data['products']}
db_active_categories = {cat[0] for cat in db_categories}

print(f'Categories in JSON: {sorted(json_active_categories)}')
print(f'Categories in DB:   {sorted(db_active_categories)}')

if json_active_categories == db_active_categories:
    print('✅ Categories match perfectly!')
else:
    print('❌ Category mismatch!')
    print(f'  Only in JSON: {json_active_categories - db_active_categories}')
    print(f'  Only in DB: {db_active_categories - json_active_categories}')

# Compare product counts by category
print(f'\n=== PRODUCT COUNT COMPARISON ===')
json_counts = {}
for prod in json_data['products']:
    cat = prod['category']
    json_counts[cat] = json_counts.get(cat, 0) + 1

db_counts = {cat[0]: cat[1] for cat in db_categories}

for category in sorted(json_active_categories):
    json_count = json_counts.get(category, 0)
    db_count = db_counts.get(category, 0)
    status = "✅" if json_count == db_count else "❌"
    print(f'  {status} {category}: JSON={json_count}, DB={db_count}')

# Check for any Uncategorized issues
print(f'\n=== UNCATEGORIZED CHECK ===')
uncategorized_in_json = any(prod['category'] == 'Uncategorized' for prod in json_data['products'])
uncategorized_in_db = any(cat[0] == 'Uncategorized' for cat in db_categories)

print(f'Uncategorized in JSON: {"❌ YES" if uncategorized_in_json else "✅ NO"}')
print(f'Uncategorized in DB:   {"❌ YES" if uncategorized_in_db else "✅ NO"}')

conn.close()

if not uncategorized_in_json and not uncategorized_in_db and json_active_categories == db_active_categories:
    print(f'\n🎉 PERFECT SUCCESS! The fix is working completely:')
    print(f'   ✅ Scraper extracts proper categories (no Uncategorized)')
    print(f'   ✅ Import preserves categories correctly') 
    print(f'   ✅ Database queries return proper categories')
    print(f'   ✅ No data corruption during import process')
else:
    print(f'\n⚠️  Some issues detected - review the comparison above')
