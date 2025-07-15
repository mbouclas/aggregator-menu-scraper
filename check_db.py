#!/usr/bin/env python3
"""Check database connection and create if needed."""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to postgres database first to check if scraper_db exists
conn_string = f"host={os.getenv('DB_HOST', 'localhost')} dbname=postgres user={os.getenv('DB_USER', 'postgres')} password={os.getenv('DB_PASSWORD', 'postgres123')}"

try:
    with psycopg2.connect(conn_string) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Check if scraper_db exists
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'scraper_db';")
            exists = cur.fetchone()
            
            if exists:
                print("✅ scraper_db database exists")
            else:
                print("❌ scraper_db database does not exist")
                print("🔧 Creating scraper_db database...")
                cur.execute("CREATE DATABASE scraper_db;")
                print("✅ Database created successfully")
    
    # Now connect to scraper_db and check schema
    conn_string = f"host={os.getenv('DB_HOST', 'localhost')} dbname=scraper_db user={os.getenv('DB_USER', 'postgres')} password={os.getenv('DB_PASSWORD', 'postgres123')}"
    
    with psycopg2.connect(conn_string) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            tables = [row[0] for row in cur.fetchall()]
            print(f"Tables in scraper_db: {tables}")
            
            if not tables:
                print("🔧 No tables found, need to run schema initialization")
            elif 'offers' not in tables:
                print("🔧 Missing offers table, need to run schema initialization")
            else:
                print("✅ Schema appears to be set up correctly")
                
except Exception as e:
    print(f"Error: {e}")
