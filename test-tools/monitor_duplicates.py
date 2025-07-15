#!/usr/bin/env python3
"""
Duplicate Prevention Monitor
===========================

This tool monitors the import process to ensure no new duplicates are created.
Run this after each scraping session to verify the fix is working.
"""

import psycopg2
import psycopg2.extras
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

def monitor_recent_imports():
    """Monitor recent import activity for duplicate prevention."""
    print("📊 Duplicate Prevention Monitor")
    print("=" * 35)
    
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Check recent product creation
    print("\n📅 Recent Product Activity (Last 24 Hours)")
    print("-" * 45)
    
    cur.execute("""
        SELECT 
            DATE_TRUNC('hour', created_at) as hour,
            COUNT(*) as products_created,
            COUNT(DISTINCT restaurant_id) as restaurants_affected
        FROM products
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY DATE_TRUNC('hour', created_at)
        ORDER BY hour DESC
        LIMIT 10
    """)
    
    recent_activity = cur.fetchall()
    
    if recent_activity:
        total_new_products = sum(row['products_created'] for row in recent_activity)
        print(f"Total new products in last 24h: {total_new_products}")
        print("\nHourly breakdown:")
        for activity in recent_activity:
            print(f"  {activity['hour'].strftime('%Y-%m-%d %H:00')}: {activity['products_created']} products, {activity['restaurants_affected']} restaurants")
    else:
        print("No products created in the last 24 hours")
    
    # Check for any duplicates that might have been created
    print("\n🔍 Duplicate Detection Check")
    print("-" * 30)
    
    cur.execute("""
        SELECT 
            restaurant_id,
            r.name as restaurant_name,
            p.name as product_name,
            COUNT(*) as count,
            ARRAY_AGG(p.id ORDER BY p.created_at) as product_ids,
            ARRAY_AGG(p.external_id ORDER BY p.created_at) as external_ids,
            MIN(p.created_at) as first_created,
            MAX(p.created_at) as last_created
        FROM products p
        JOIN restaurants r ON p.restaurant_id = r.id
        GROUP BY restaurant_id, r.name, p.name
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC, last_created DESC
        LIMIT 5
    """)
    
    duplicates = cur.fetchall()
    
    if duplicates:
        print(f"⚠️  Found {len(duplicates)} products with multiple entries:")
        for dup in duplicates:
            print(f"\n  🏪 {dup['restaurant_name']}")
            print(f"     Product: '{dup['product_name']}'")
            print(f"     Count: {dup['count']}")
            print(f"     Created: {dup['first_created']} → {dup['last_created']}")
            print(f"     External IDs: {dup['external_ids']}")
            
            # Check if this is a recent duplicate (created in last 24h)
            time_diff = dup['last_created'] - dup['first_created']
            if time_diff < timedelta(days=1):
                print(f"     🚨 RECENT DUPLICATE DETECTED! Time diff: {time_diff}")
            else:
                print(f"     ℹ️  Old duplicate (time diff: {time_diff.days} days)")
    else:
        print("✅ No duplicate products found")
    
    # Check product external_id updates (indicating fix is working)
    print("\n🔄 External ID Updates (Fix Working)")
    print("-" * 40)
    
    cur.execute("""
        SELECT 
            p.name as product_name,
            r.name as restaurant_name,
            p.external_id,
            p.updated_at
        FROM products p
        JOIN restaurants r ON p.restaurant_id = r.id
        WHERE p.updated_at > p.created_at
        AND p.updated_at >= NOW() - INTERVAL '24 hours'
        ORDER BY p.updated_at DESC
        LIMIT 10
    """)
    
    updates = cur.fetchall()
    
    if updates:
        print(f"Found {len(updates)} product updates in last 24h (fix is working):")
        for update in updates:
            print(f"  📝 {update['restaurant_name']}: '{update['product_name']}'")
            print(f"     External ID: {update['external_id']}, Updated: {update['updated_at']}")
    else:
        print("No product updates in last 24h")
    
    # Database health summary
    print("\n📊 Database Health Summary")
    print("-" * 28)
    
    cur.execute("SELECT COUNT(*) as total_products FROM products")
    total_products = cur.fetchone()['total_products']
    
    cur.execute("SELECT COUNT(DISTINCT restaurant_id) as total_restaurants FROM products")
    total_restaurants = cur.fetchone()['total_restaurants']
    
    cur.execute("""
        SELECT COUNT(*) as unique_products 
        FROM (
            SELECT restaurant_id, name 
            FROM products 
            GROUP BY restaurant_id, name
        ) t
    """)
    unique_products = cur.fetchone()['unique_products']
    
    duplicate_ratio = ((total_products - unique_products) / total_products * 100) if total_products > 0 else 0
    
    print(f"Total products: {total_products}")
    print(f"Unique products: {unique_products}")
    print(f"Total restaurants: {total_restaurants}")
    print(f"Duplicate ratio: {duplicate_ratio:.2f}%")
    
    if duplicate_ratio == 0:
        print("✅ Perfect data integrity - no duplicates!")
    elif duplicate_ratio < 1:
        print("✅ Excellent data integrity - minimal duplicates")
    elif duplicate_ratio < 5:
        print("⚠️  Good data integrity - some duplicates remain")
    else:
        print("🚨 Poor data integrity - many duplicates found")
    
    conn.close()

def create_monitoring_script():
    """Create a monitoring script for regular use."""
    print("\n🔧 Creating Monitoring Script")
    print("-" * 30)
    
    script_content = """@echo off
echo Running Duplicate Prevention Monitor...
cd /d "C:\\work\\aggregator-menu-scraper\\test-tools"
"C:/Users/mbouklas/.pyenv/pyenv-win/versions/3.12.7/python.exe" monitor_duplicates.py
pause
"""
    
    script_path = Path(__file__).parent.parent / 'monitor_duplicates.bat'
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"✅ Created monitoring script: {script_path}")
    print("💡 Run this script after each scraping session to check for duplicates")

if __name__ == "__main__":
    monitor_recent_imports()
    create_monitoring_script()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Run a test scrape to verify the fix works")
    print("2. Monitor the logs for external_id updates")
    print("3. Use monitor_duplicates.bat for regular checks")
    print("4. Report any duplicate creation issues immediately")
