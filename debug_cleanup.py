#!/usr/bin/env python3
import psycopg2
import psycopg2.extras
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from database directory
env_path = Path(__file__).parent / 'database' / '.env'
load_dotenv(env_path)

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Test the exact duplicate query
query = """
SELECT 
    p.restaurant_id,
    r.name as restaurant_name,
    p.name,
    ARRAY_AGG(p.id ORDER BY p.created_at) as product_ids,
    COUNT(*) as duplicate_count
FROM products p
JOIN restaurants r ON p.restaurant_id = r.id
GROUP BY p.restaurant_id, r.name, p.name
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, r.name, p.name
LIMIT 2;
"""

cur.execute(query)
results = cur.fetchall()

for row in results:
    print(f"Restaurant: {row['restaurant_name']}")
    print(f"Product: {row['name']}")
    print(f"Product IDs: {row['product_ids']}")
    print(f"Type of first ID: {type(row['product_ids'][0])}")
    print(f"First ID: {repr(row['product_ids'][0])}")
    print("---")

conn.close()
