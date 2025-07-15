#!/usr/bin/env python3
"""
Validate Caffè Nero Offer Import
================================
Check that our discount fixes worked correctly in the database.
"""

import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Query database to validate Caffè Nero offer import."""
    
    conn_string = (
        f"host={os.getenv('DB_HOST', 'localhost')} "
        f"dbname={os.getenv('DB_NAME', 'scraper_db')} "
        f"user={os.getenv('DB_USER', 'postgres')} "
        f"password={os.getenv('DB_PASSWORD', 'postgres123')}"
    )
    
    print("🔍 Validating Caffè Nero Offer Import")
    print("=" * 50)
    
    try:
        with psycopg2.connect(conn_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                
                # 1. Check Caffè Nero offers
                print("📊 Caffè Nero Offers:")
                cur.execute("""
                    SELECT o.name, o.discount_percentage, o.offer_type, 
                           COUNT(pp.id) as product_count
                    FROM offers o
                    JOIN restaurants r ON o.restaurant_id = r.id
                    LEFT JOIN product_prices pp ON pp.offer_id = o.id
                    WHERE r.name LIKE '%Caffè Nero%'
                    GROUP BY o.id, o.name, o.discount_percentage, o.offer_type
                    ORDER BY o.discount_percentage DESC NULLS LAST;
                """)
                
                for row in cur.fetchall():
                    discount = f"{row['discount_percentage']}%" if row['discount_percentage'] else "N/A"
                    print(f"   • {row['name']}")
                    print(f"     - Discount: {discount}")
                    print(f"     - Type: {row['offer_type']}")
                    print(f"     - Products: {row['product_count']}")
                
                print()
                
                # 2. Check products with offers and their discount calculations
                print("💰 Products with Calculated Discounts:")
                cur.execute("""
                    SELECT p.name as product_name,
                           pp.price,
                           pp.original_price,
                           pp.discount_percentage,
                           CASE 
                               WHEN pp.discount_percentage > 0 THEN (pp.original_price - pp.price)
                               ELSE 0
                           END as discount_amount,
                           o.name as offer_name
                    FROM product_prices pp
                    JOIN products p ON pp.product_id = p.id
                    JOIN restaurants r ON p.restaurant_id = r.id
                    LEFT JOIN offers o ON pp.offer_id = o.id
                    WHERE r.name LIKE '%Caffè Nero%'
                      AND pp.discount_percentage > 0
                    ORDER BY (pp.original_price - pp.price) DESC;
                """)
                
                total_savings = 0
                for row in cur.fetchall():
                    savings = row['discount_amount'] or 0
                    total_savings += savings
                    print(f"   • {row['product_name'][:40]}...")
                    print(f"     - Price: €{row['price']:.2f}")
                    print(f"     - Original: €{row['original_price']:.2f}")
                    print(f"     - Savings: €{savings:.2f} ({row['discount_percentage']}%)")
                    print(f"     - Offer: {row['offer_name']}")
                    print()
                
                print(f"💰 Total Savings Tracked: €{total_savings:.2f}")
                
                # 3. Validate no NULL discount data
                print("\n🔍 Checking for NULL discount data:")
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM product_prices pp
                    JOIN products p ON pp.product_id = p.id
                    JOIN restaurants r ON p.restaurant_id = r.id
                    WHERE r.name LIKE '%Caffè Nero%'
                      AND pp.discount_percentage > 0
                      AND (pp.original_price IS NULL);
                """)
                
                result = cur.fetchone()
                null_count = result['count'] if result else 0
                if null_count == 0:
                    print("   ✅ No NULL original prices found!")
                else:
                    print(f"   ❌ Found {null_count} records with NULL original prices")
                
                # 4. Summary
                print(f"\n📋 Summary:")
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT o.id) as offer_count,
                        COUNT(DISTINCT CASE WHEN pp.discount_percentage > 0 THEN pp.id END) as discounted_products,
                        COALESCE(SUM(CASE WHEN pp.discount_percentage > 0 THEN (pp.original_price - pp.price) ELSE 0 END), 0) as total_discount_amount
                    FROM restaurants r
                    LEFT JOIN offers o ON o.restaurant_id = r.id
                    LEFT JOIN product_prices pp ON pp.offer_id = o.id
                    WHERE r.name LIKE '%Caffè Nero%';
                """)
                
                summary = cur.fetchone()
                if summary:
                    print(f"   ✅ Offers created: {summary['offer_count']}")
                    print(f"   ✅ Discounted products: {summary['discounted_products']}")
                    print(f"   ✅ Total discount amount: €{summary['total_discount_amount']:.2f}")
                else:
                    print("   ❌ No summary data found")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
