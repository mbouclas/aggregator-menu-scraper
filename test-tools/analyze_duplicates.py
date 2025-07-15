#!/usr/bin/env python3
"""
Duplicate Analysis Tool
======================

This tool analyzes how duplicates were created during the import process.
It examines the existing database to understand the patterns of duplicate creation.
"""

import psycopg2
import psycopg2.extras
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from collections import defaultdict
from datetime import datetime

def load_db_config():
    """Load database configuration from database/.env file."""
    env_path = Path(__file__).parent.parent / 'database' / '.env'
    load_dotenv(env_path)
    
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'scraper_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres123')
    }

def connect_to_db():
    """Connect to PostgreSQL database."""
    config = load_db_config()
    return psycopg2.connect(**config)

def analyze_import_patterns():
    """Analyze the patterns that led to duplicate creation."""
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    print("🔍 Analyzing Import Patterns That Created Duplicates")
    print("=" * 60)
    
    # 1. Analyze products with same external_id but different names
    print("\n📋 Analysis 1: Products with Same External ID but Different Names")
    print("-" * 50)
    cur.execute("""
        SELECT 
            restaurant_id,
            r.name as restaurant_name,
            external_id,
            COUNT(DISTINCT name) as name_variations,
            ARRAY_AGG(DISTINCT name ORDER BY name) as names,
            ARRAY_AGG(DISTINCT id ORDER BY created_at) as product_ids,
            MIN(created_at) as first_created,
            MAX(created_at) as last_created
        FROM products p
        JOIN restaurants r ON p.restaurant_id = r.id
        WHERE external_id IS NOT NULL
        GROUP BY restaurant_id, r.name, external_id
        HAVING COUNT(DISTINCT name) > 1
        ORDER BY name_variations DESC, restaurant_name
        LIMIT 10
    """)
    
    external_id_conflicts = cur.fetchall()
    if external_id_conflicts:
        print(f"Found {len(external_id_conflicts)} external ID conflicts with name variations:")
        for conflict in external_id_conflicts:
            print(f"  🏪 {conflict['restaurant_name']}")
            print(f"     External ID: {conflict['external_id']}")
            print(f"     Name variations ({conflict['name_variations']}): {conflict['names']}")
            print(f"     Created: {conflict['first_created']} → {conflict['last_created']}")
            print()
    else:
        print("✅ No external ID conflicts with name variations found")
    
    # 2. Analyze products with same name but different external_ids
    print("\n📋 Analysis 2: Products with Same Name but Different External IDs")
    print("-" * 50)
    cur.execute("""
        SELECT 
            restaurant_id,
            r.name as restaurant_name,
            p.name as product_name,
            COUNT(DISTINCT external_id) as external_id_variations,
            ARRAY_AGG(DISTINCT external_id ORDER BY external_id) as external_ids,
            ARRAY_AGG(DISTINCT id ORDER BY created_at) as product_ids,
            MIN(created_at) as first_created,
            MAX(created_at) as last_created
        FROM products p
        JOIN restaurants r ON p.restaurant_id = r.id
        WHERE external_id IS NOT NULL
        GROUP BY restaurant_id, r.name, p.name
        HAVING COUNT(DISTINCT external_id) > 1
        ORDER BY external_id_variations DESC, restaurant_name
        LIMIT 10
    """)
    
    name_conflicts = cur.fetchall()
    if name_conflicts:
        print(f"Found {len(name_conflicts)} name conflicts with external ID variations:")
        for conflict in name_conflicts:
            print(f"  🏪 {conflict['restaurant_name']}")
            print(f"     Product: {conflict['product_name']}")
            print(f"     External ID variations ({conflict['external_id_variations']}): {conflict['external_ids']}")
            print(f"     Created: {conflict['first_created']} → {conflict['last_created']}")
            print()
    else:
        print("✅ No name conflicts with external ID variations found")
    
    # 3. Analyze products with NULL external_id (these likely created duplicates)
    print("\n📋 Analysis 3: Products with NULL External IDs")
    print("-" * 50)
    cur.execute("""
        SELECT 
            restaurant_id,
            r.name as restaurant_name,
            COUNT(*) as null_external_id_count,
            COUNT(DISTINCT p.name) as unique_names,
            ARRAY_AGG(DISTINCT p.name ORDER BY p.name) as sample_names
        FROM products p
        JOIN restaurants r ON p.restaurant_id = r.id
        WHERE external_id IS NULL
        GROUP BY restaurant_id, r.name
        HAVING COUNT(*) > 0
        ORDER BY null_external_id_count DESC
        LIMIT 10
    """)
    
    null_external_ids = cur.fetchall()
    if null_external_ids:
        print(f"Found products with NULL external IDs:")
        for row in null_external_ids:
            print(f"  🏪 {row['restaurant_name']}: {row['null_external_id_count']} products with NULL external_id")
            print(f"     Unique names: {row['unique_names']}")
            if len(row['sample_names']) <= 5:
                print(f"     Names: {row['sample_names']}")
            else:
                print(f"     Sample names: {row['sample_names'][:5]}... (showing first 5)")
            print()
    else:
        print("✅ No products with NULL external IDs found")
    
    # 4. Analyze creation timeline patterns
    print("\n📋 Analysis 4: Creation Timeline Patterns")
    print("-" * 50)
    cur.execute("""
        SELECT 
            DATE_TRUNC('day', created_at) as creation_day,
            COUNT(*) as products_created,
            COUNT(DISTINCT restaurant_id) as restaurants_affected
        FROM products
        GROUP BY DATE_TRUNC('day', created_at)
        ORDER BY creation_day DESC
        LIMIT 10
    """)
    
    timeline = cur.fetchall()
    print("Recent product creation activity:")
    for day in timeline:
        print(f"  📅 {day['creation_day'].strftime('%Y-%m-%d')}: {day['products_created']} products across {day['restaurants_affected']} restaurants")
    
    # 5. Check price records to understand scraping frequency
    print("\n📋 Analysis 5: Scraping Frequency Analysis")
    print("-" * 50)
    cur.execute("""
        SELECT 
            DATE_TRUNC('day', scraped_at) as scrape_day,
            COUNT(DISTINCT restaurant_id) as restaurants_scraped,
            COUNT(*) as price_records,
            COUNT(DISTINCT product_id) as unique_products
        FROM product_prices pp
        JOIN products p ON pp.product_id = p.id
        GROUP BY DATE_TRUNC('day', scraped_at)
        ORDER BY scrape_day DESC
        LIMIT 10
    """)
    
    scraping = cur.fetchall()
    print("Recent scraping activity:")
    for day in scraping:
        print(f"  📅 {day['scrape_day'].strftime('%Y-%m-%d')}: {day['restaurants_scraped']} restaurants, {day['price_records']} price records, {day['unique_products']} unique products")
    
    conn.close()

def analyze_external_id_patterns():
    """Analyze external ID patterns to understand scraper behavior."""
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    print("\n🔍 Analyzing External ID Patterns")
    print("=" * 40)
    
    # Check external ID formats by restaurant
    cur.execute("""
        SELECT 
            r.name as restaurant_name,
            COUNT(*) as total_products,
            COUNT(CASE WHEN external_id IS NOT NULL THEN 1 END) as with_external_id,
            COUNT(CASE WHEN external_id IS NULL THEN 1 END) as without_external_id,
            ARRAY_AGG(DISTINCT 
                CASE 
                    WHEN external_id IS NOT NULL 
                    THEN SUBSTRING(external_id, 1, 20) 
                END 
                ORDER BY external_id
            ) FILTER (WHERE external_id IS NOT NULL) as sample_external_ids
        FROM products p
        JOIN restaurants r ON p.restaurant_id = r.id
        GROUP BY r.name
        ORDER BY without_external_id DESC, total_products DESC
    """)
    
    patterns = cur.fetchall()
    print("External ID patterns by restaurant:")
    for pattern in patterns:
        print(f"  🏪 {pattern['restaurant_name']}")
        print(f"     Total: {pattern['total_products']}, With external_id: {pattern['with_external_id']}, Without: {pattern['without_external_id']}")
        if pattern['sample_external_ids']:
            sample_ids = [id for id in pattern['sample_external_ids'] if id][:3]
            print(f"     Sample external IDs: {sample_ids}")
        print()
    
    conn.close()

if __name__ == "__main__":
    analyze_import_patterns()
    analyze_external_id_patterns()
