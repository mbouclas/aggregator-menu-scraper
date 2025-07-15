#!/usr/bin/env python3
"""
Product Uniqueness Verification
===============================
Check for duplicate products within each restaurant in the database.
"""

import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from database/.env file
env_path = Path(__file__).parent / 'database' / '.env'
load_dotenv(env_path)

def main():
    """Verify product uniqueness within each restaurant."""
    
    conn_string = (
        f"host={os.getenv('DB_HOST', 'localhost')} "
        f"port={os.getenv('DB_PORT', '5432')} "
        f"dbname={os.getenv('DB_NAME', 'scraper_db')} "
        f"user={os.getenv('DB_USER', 'postgres')} "
        f"password={os.getenv('DB_PASSWORD', 'postgres123')}"
    )
    
    print("🔍 Verifying Product Uniqueness per Restaurant")
    print("=" * 70)
    
    try:
        with psycopg2.connect(conn_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                
                # Check 1: Exact name duplicates within same restaurant
                print("📊 Check 1: Exact Product Name Duplicates")
                print("-" * 50)
                
                cur.execute("""
                    SELECT 
                        r.name as restaurant_name,
                        p.name as product_name,
                        COUNT(*) as duplicate_count,
                        ARRAY_AGG(p.id) as product_ids,
                        ARRAY_AGG(p.created_at) as created_dates
                    FROM products p
                    JOIN restaurants r ON p.restaurant_id = r.id
                    GROUP BY r.id, r.name, p.name
                    HAVING COUNT(*) > 1
                    ORDER BY duplicate_count DESC, r.name, p.name;
                """)
                
                exact_duplicates = cur.fetchall()
                
                if exact_duplicates:
                    print(f"❌ Found {len(exact_duplicates)} sets of exact name duplicates:")
                    for dup in exact_duplicates:
                        print(f"\n🏪 {dup['restaurant_name']}")
                        print(f"   📦 Product: '{dup['product_name']}'")
                        print(f"   🔢 Count: {dup['duplicate_count']} duplicates")
                        print(f"   🆔 IDs: {', '.join(dup['product_ids'])}")
                        print(f"   📅 Created: {', '.join([str(d.date()) for d in dup['created_dates']])}")
                else:
                    print("✅ No exact name duplicates found!")
                
                # Check 2: Similar name duplicates (case insensitive, whitespace variations)
                print(f"\n📊 Check 2: Similar Product Name Duplicates")
                print("-" * 50)
                
                cur.execute("""
                    SELECT 
                        r.name as restaurant_name,
                        TRIM(LOWER(p.name)) as normalized_name,
                        COUNT(*) as duplicate_count,
                        ARRAY_AGG(p.name) as original_names,
                        ARRAY_AGG(p.id) as product_ids
                    FROM products p
                    JOIN restaurants r ON p.restaurant_id = r.id
                    GROUP BY r.id, r.name, TRIM(LOWER(p.name))
                    HAVING COUNT(*) > 1
                    ORDER BY duplicate_count DESC, r.name;
                """)
                
                similar_duplicates = cur.fetchall()
                
                if similar_duplicates:
                    print(f"❌ Found {len(similar_duplicates)} sets of similar name duplicates:")
                    for dup in similar_duplicates:
                        print(f"\n🏪 {dup['restaurant_name']}")
                        print(f"   🔤 Normalized: '{dup['normalized_name']}'")
                        print(f"   🔢 Count: {dup['duplicate_count']} variations")
                        print(f"   📝 Original names: {dup['original_names']}")
                        print(f"   🆔 IDs: {', '.join(dup['product_ids'])}")
                else:
                    print("✅ No similar name duplicates found!")
                
                # Check 3: Products with same name but different external IDs
                print(f"\n📊 Check 3: Same Name, Different External IDs")
                print("-" * 50)
                
                cur.execute("""
                    SELECT 
                        r.name as restaurant_name,
                        p.name as product_name,
                        COUNT(DISTINCT p.external_id) as external_id_count,
                        ARRAY_AGG(DISTINCT p.external_id) as external_ids,
                        ARRAY_AGG(p.id) as product_ids
                    FROM products p
                    JOIN restaurants r ON p.restaurant_id = r.id
                    WHERE p.external_id IS NOT NULL
                    GROUP BY r.id, r.name, p.name
                    HAVING COUNT(DISTINCT p.external_id) > 1
                    ORDER BY external_id_count DESC, r.name, p.name;
                """)
                
                external_id_conflicts = cur.fetchall()
                
                if external_id_conflicts:
                    print(f"❌ Found {len(external_id_conflicts)} products with conflicting external IDs:")
                    for conflict in external_id_conflicts:
                        print(f"\n🏪 {conflict['restaurant_name']}")
                        print(f"   📦 Product: '{conflict['product_name']}'")
                        print(f"   🔢 External ID count: {conflict['external_id_count']}")
                        print(f"   🆔 External IDs: {conflict['external_ids']}")
                        print(f"   🔗 Product IDs: {', '.join(conflict['product_ids'])}")
                else:
                    print("✅ No external ID conflicts found!")
                
                # Check 4: Overall statistics
                print(f"\n📊 Overall Database Statistics")
                print("-" * 50)
                
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT r.id) as total_restaurants,
                        COUNT(p.id) as total_products,
                        COUNT(DISTINCT p.name) as unique_product_names,
                        COUNT(p.id) - COUNT(DISTINCT p.name) as potential_duplicates
                    FROM products p
                    JOIN restaurants r ON p.restaurant_id = r.id;
                """)
                
                stats = cur.fetchone()
                if stats:
                    print(f"   🏪 Total restaurants: {stats['total_restaurants']}")
                    print(f"   📦 Total products: {stats['total_products']}")
                    print(f"   🔤 Unique product names: {stats['unique_product_names']}")
                    print(f"   ⚠️  Potential name reuse: {stats['potential_duplicates']}")
                else:
                    print("   ❌ No statistics available")
                
                # Check 5: Products per restaurant breakdown
                print(f"\n📊 Products per Restaurant")
                print("-" * 50)
                
                cur.execute("""
                    SELECT 
                        r.name as restaurant_name,
                        COUNT(p.id) as total_products,
                        COUNT(DISTINCT p.name) as unique_names,
                        COUNT(p.id) - COUNT(DISTINCT p.name) as name_duplicates
                    FROM restaurants r
                    LEFT JOIN products p ON r.id = p.restaurant_id
                    GROUP BY r.id, r.name
                    HAVING COUNT(p.id) > 0
                    ORDER BY name_duplicates DESC, total_products DESC;
                """)
                
                restaurant_stats = cur.fetchall()
                
                print("Restaurant breakdown:")
                problematic_restaurants = 0
                for rst in restaurant_stats:
                    status = "❌" if rst['name_duplicates'] > 0 else "✅"
                    print(f"   {status} {rst['restaurant_name']}: {rst['total_products']} products, "
                          f"{rst['unique_names']} unique names, {rst['name_duplicates']} duplicates")
                    if rst['name_duplicates'] > 0:
                        problematic_restaurants += 1
                
                # Summary
                print(f"\n🎯 SUMMARY")
                print("=" * 70)
                
                total_issues = len(exact_duplicates) + len(similar_duplicates) + len(external_id_conflicts)
                
                if total_issues == 0:
                    print("✅ SUCCESS: All products are unique within their restaurants!")
                    print("   No action needed.")
                else:
                    print(f"❌ ISSUES FOUND: {total_issues} uniqueness problems detected")
                    print(f"   • {len(exact_duplicates)} exact name duplicates")
                    print(f"   • {len(similar_duplicates)} similar name duplicates") 
                    print(f"   • {len(external_id_conflicts)} external ID conflicts")
                    print(f"   • {problematic_restaurants} restaurants affected")
                    print(f"\n⚠️  RECOMMENDATION: Manual review required")
                    print(f"   Some products may need to be merged or cleaned up.")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
