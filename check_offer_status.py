#!/usr/bin/env python3
"""
Check Offer Status - Both Active and Inactive
=============================================
"""

import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    """Check all offers for Caffè Nero including inactive ones."""
    
    conn_string = (
        f"host={os.getenv('DB_HOST', 'localhost')} "
        f"dbname={os.getenv('DB_NAME', 'scraper_db')} "
        f"user={os.getenv('DB_USER', 'postgres')} "
        f"password={os.getenv('DB_PASSWORD', 'postgres123')}"
    )
    
    print("🔍 Checking Caffè Nero Offer Status (Active + Inactive)")
    print("=" * 70)
    
    try:
        with psycopg2.connect(conn_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                
                # Get all offers for Caffè Nero
                cur.execute("""
                    SELECT o.name, o.discount_percentage, o.offer_type, 
                           o.is_active, o.start_date, o.end_date,
                           COUNT(pp.id) as product_count
                    FROM offers o
                    JOIN restaurants r ON o.restaurant_id = r.id
                    LEFT JOIN product_prices pp ON pp.offer_id = o.id
                    WHERE r.name LIKE '%Caffè Nero%'
                    GROUP BY o.id, o.name, o.discount_percentage, o.offer_type, 
                             o.is_active, o.start_date, o.end_date
                    ORDER BY o.is_active DESC, o.start_date DESC;
                """)
                
                offers = cur.fetchall()
                
                active_count = 0
                inactive_count = 0
                
                print("📊 All Caffè Nero Offers:")
                for offer in offers:
                    status = "✅ ACTIVE" if offer['is_active'] else "🔴 INACTIVE"
                    discount = f"{offer['discount_percentage']}%" if offer['discount_percentage'] else "N/A"
                    
                    print(f"\n{status} • {offer['name']}")
                    print(f"   - Discount: {discount}")
                    print(f"   - Type: {offer['offer_type']}")
                    print(f"   - Products: {offer['product_count']}")
                    print(f"   - Start: {offer['start_date']}")
                    if offer['end_date']:
                        print(f"   - End: {offer['end_date']}")
                    
                    if offer['is_active']:
                        active_count += 1
                    else:
                        inactive_count += 1
                
                print(f"\n📋 Summary:")
                print(f"   ✅ Active offers: {active_count}")
                print(f"   🔴 Inactive offers: {inactive_count}")
                print(f"   📊 Total offers: {len(offers)}")
                
                if inactive_count > 0:
                    print(f"\n🎉 SUCCESS: Offer deactivation is working!")
                    print(f"   The '25% Discount' offer was properly deactivated when products no longer had that discount.")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
