#!/usr/bin/env python3
"""Check database tables."""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn_string = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"dbname={os.getenv('DB_NAME', 'postgres')} "
    f"user={os.getenv('DB_USER', 'postgres')} "
    f"password={os.getenv('DB_PASSWORD', 'postgres123')}"
)

try:
    with psycopg2.connect(conn_string) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
            tables = [row[0] for row in cur.fetchall()]
            print(f"Database tables: {tables}")
            
            # Check if offers table exists
            if 'offers' in tables:
                cur.execute("SELECT COUNT(*) FROM offers;")
                count = cur.fetchone()[0]
                print(f"Offers table exists with {count} records")
            else:
                print("❌ Offers table does not exist")
                
except Exception as e:
    print(f"Error: {e}")
