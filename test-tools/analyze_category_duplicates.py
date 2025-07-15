#!/usr/bin/env python3
"""
Category Duplicate Analysis Tool
===============================

This tool analyzes category duplicates and identifies issues with category import logic.
"""

import psycopg2
import psycopg2.extras
import os
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime

def load_db_config():
    """Load database configuration from database/.env file."""
    env_path = Path(__file__).parent.parent / 'database' / '.env'
    load_dotenv(env_path)
    
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'scraper_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres123')
    }

def connect_to_db():
    """Connect to PostgreSQL database."""
    config = load_db_config()
    return psycopg2.connect(**config)

def analyze_category_duplicates():
    """Analyze category duplicates in the database."""
    print("🔍 Category Duplicate Analysis")
    print("=" * 35)
    
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Check for duplicate categories within same restaurant
    print("\n📋 Analysis 1: Duplicate Categories per Restaurant")
    print("-" * 50)
    cur.execute("""
        SELECT 
            restaurant_id,
            r.name as restaurant_name,
            c.name as category_name,
            COUNT(*) as duplicate_count,
            ARRAY_AGG(c.id ORDER BY c.created_at) as category_ids,
            ARRAY_AGG(c.description ORDER BY c.created_at) as descriptions,
            ARRAY_AGG(c.display_order ORDER BY c.created_at) as display_orders,
            ARRAY_AGG(c.source ORDER BY c.created_at) as sources,
            MIN(c.created_at) as first_created,
            MAX(c.created_at) as last_created
        FROM categories c
        JOIN restaurants r ON c.restaurant_id = r.id
        GROUP BY restaurant_id, r.name, c.name
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC, restaurant_name, category_name
    """)
    
    category_duplicates = cur.fetchall()
    
    if category_duplicates:
        print(f"🚨 Found {len(category_duplicates)} category names with duplicates:")
        total_duplicate_categories = sum(dup['duplicate_count'] for dup in category_duplicates)
        excess_categories = sum(dup['duplicate_count'] - 1 for dup in category_duplicates)
        
        print(f"📊 Total duplicate category records: {total_duplicate_categories}")
        print(f"📊 Excess categories to remove: {excess_categories}")
        print()
        
        for dup in category_duplicates:
            print(f"  🏪 {dup['restaurant_name']}")
            print(f"     Category: '{dup['category_name']}'")
            print(f"     Duplicates: {dup['duplicate_count']}")
            print(f"     IDs: {dup['category_ids']}")
            print(f"     Descriptions: {dup['descriptions']}")
            print(f"     Display Orders: {dup['display_orders']}")
            print(f"     Sources: {dup['sources']}")
            print(f"     Created: {dup['first_created']} → {dup['last_created']}")
            
            # Check products using these categories
            category_ids_str = "', '".join(dup['category_ids'])
            cur.execute(f"""
                SELECT category_id, COUNT(*) as product_count
                FROM products 
                WHERE category_id IN ('{category_ids_str}')
                GROUP BY category_id
                ORDER BY product_count DESC
            """)
            product_usage = cur.fetchall()
            
            if product_usage:
                print(f"     Product usage by category_id:")
                for usage in product_usage:
                    print(f"       - {usage['category_id']}: {usage['product_count']} products")
            else:
                print(f"     📝 No products using these categories")
            print()
    else:
        print("✅ No duplicate categories found")
    
    # Check categories by restaurant summary
    print("\n📋 Analysis 2: Categories per Restaurant Summary")
    print("-" * 50)
    cur.execute("""
        SELECT 
            r.name as restaurant_name,
            COUNT(*) as total_categories,
            COUNT(DISTINCT c.name) as unique_category_names,
            COUNT(*) - COUNT(DISTINCT c.name) as duplicate_categories
        FROM categories c
        JOIN restaurants r ON c.restaurant_id = r.id
        GROUP BY r.name
        HAVING COUNT(*) - COUNT(DISTINCT c.name) > 0
        ORDER BY duplicate_categories DESC, total_categories DESC
    """)
    
    restaurant_summary = cur.fetchall()
    
    if restaurant_summary:
        print(f"Restaurants with duplicate categories:")
        for summary in restaurant_summary:
            print(f"  🏪 {summary['restaurant_name']}")
            print(f"     Total categories: {summary['total_categories']}")
            print(f"     Unique names: {summary['unique_category_names']}")
            print(f"     Duplicates: {summary['duplicate_categories']}")
            print()
    else:
        print("✅ All restaurants have unique category names")
    
    # Check recent category creation patterns
    print("\n📋 Analysis 3: Recent Category Creation Patterns")
    print("-" * 50)
    cur.execute("""
        SELECT 
            DATE_TRUNC('day', created_at) as creation_day,
            COUNT(*) as categories_created,
            COUNT(DISTINCT restaurant_id) as restaurants_affected,
            COUNT(DISTINCT name) as unique_names
        FROM categories
        WHERE created_at >= NOW() - INTERVAL '7 days'
        GROUP BY DATE_TRUNC('day', created_at)
        ORDER BY creation_day DESC
    """)
    
    recent_creation = cur.fetchall()
    
    if recent_creation:
        print("Recent category creation (last 7 days):")
        for day in recent_creation:
            duplicate_ratio = ((day['categories_created'] - day['unique_names']) / day['categories_created'] * 100) if day['categories_created'] > 0 else 0
            print(f"  📅 {day['creation_day'].strftime('%Y-%m-%d')}: {day['categories_created']} categories, {day['unique_names']} unique names")
            print(f"      Restaurants: {day['restaurants_affected']}, Duplicate ratio: {duplicate_ratio:.1f}%")
    else:
        print("No categories created in the last 7 days")
    
    conn.close()
    
    return len(category_duplicates) > 0

def analyze_category_schema():
    """Analyze the category table schema and constraints."""
    print("\n🔍 Category Schema Analysis")
    print("=" * 30)
    
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Check table constraints
    cur.execute("""
        SELECT 
            conname as constraint_name,
            contype as constraint_type,
            pg_get_constraintdef(oid) as constraint_definition
        FROM pg_constraint 
        WHERE conrelid = 'categories'::regclass
        ORDER BY contype, conname
    """)
    
    constraints = cur.fetchall()
    
    print("Current constraints on categories table:")
    for constraint in constraints:
        constraint_type_map = {
            'p': 'PRIMARY KEY',
            'u': 'UNIQUE',
            'f': 'FOREIGN KEY',
            'c': 'CHECK'
        }
        type_name = constraint_type_map.get(constraint['constraint_type'], constraint['constraint_type'])
        print(f"  {type_name}: {constraint['constraint_name']}")
        print(f"    Definition: {constraint['constraint_definition']}")
    
    # Check indexes
    cur.execute("""
        SELECT 
            indexname,
            indexdef
        FROM pg_indexes 
        WHERE tablename = 'categories'
        ORDER BY indexname
    """)
    
    indexes = cur.fetchall()
    
    print(f"\nIndexes on categories table:")
    for index in indexes:
        print(f"  {index['indexname']}: {index['indexdef']}")
    
    conn.close()

if __name__ == "__main__":
    has_duplicates = analyze_category_duplicates()
    analyze_category_schema()
    
    if has_duplicates:
        print("\n🚨 ACTION REQUIRED:")
        print("1. Category duplicates found that need cleanup")
        print("2. Import logic may need fixing to prevent future duplicates")
        print("3. Run the category cleanup tool to resolve duplicates")
    else:
        print("\n✅ CATEGORY SYSTEM HEALTHY:")
        print("1. No duplicate categories found")
        print("2. Import logic appears to be working correctly")
        print("3. All restaurants have unique category names")
