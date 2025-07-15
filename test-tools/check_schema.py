#!/usr/bin/env python3
import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from database directory
env_path = Path(__file__).parent / 'database' / '.env'
load_dotenv(env_path)

try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    cur = conn.cursor()
    
    # Get all tables
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = [row[0] for row in cur.fetchall()]
    print("Tables:", tables)
    
    # Check key tables
    for table in ['products', 'restaurants', 'offers', 'product_prices']:
        if table in tables:
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'")
            columns = [row[0] for row in cur.fetchall()]
            print(f"{table} columns:", columns)
        else:
            print(f"{table} table not found")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
