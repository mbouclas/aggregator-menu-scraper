#!/usr/bin/env python3
"""
Verify Offers Table Cleanup
===========================
Verify that all offers now have proper discount data.
"""

import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    """Verify the offers table is clean."""
    
    conn_string = (
        f"host={os.getenv('DB_HOST', 'localhost')} "
        f"dbname={os.getenv('DB_NAME', 'scraper_db')} "
        f"user={os.getenv('DB_USER', 'postgres')} "
        f"password={os.getenv('DB_PASSWORD', 'postgres123')}"
    )
    
    print("✅ Verifying Offers Table After Cleanup")
    print("=" * 60)
    
    try:
        with psycopg2.connect(conn_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                
                # Check for any remaining NULL discount offers
                cur.execute("""
                    SELECT COUNT(*) as null_count 
                    FROM offers 
                    WHERE discount_percentage IS NULL AND discount_amount IS NULL;
                """)
                result = cur.fetchone()
                null_count = result['null_count'] if result else 0
                
                if null_count == 0:
                    print("✅ SUCCESS: No offers with NULL discount values found!")
                else:
                    print(f"❌ WARNING: {null_count} offers still have NULL discount values")
                
                # Show all remaining offers
                print(f"\n📊 All Remaining Offers:")
                cur.execute("""
                    SELECT r.name as restaurant_name, o.name as offer_name, 
                           o.discount_percentage, o.discount_amount, o.offer_type,
                           o.is_active, COUNT(pp.id) as product_count
                    FROM offers o
                    JOIN restaurants r ON o.restaurant_id = r.id
                    LEFT JOIN product_prices pp ON pp.offer_id = o.id
                    GROUP BY o.id, r.name, o.name, o.discount_percentage, 
                             o.discount_amount, o.offer_type, o.is_active
                    ORDER BY r.name, o.discount_percentage DESC NULLS LAST;
                """)
                
                offers = cur.fetchall()
                
                print(f"Total remaining offers: {len(offers)}")
                print()
                
                for offer in offers:
                    status = "✅ ACTIVE" if offer['is_active'] else "🔴 INACTIVE"
                    discount_pct = f"{offer['discount_percentage']}%" if offer['discount_percentage'] else "N/A"
                    discount_amt = f"€{offer['discount_amount']}" if offer['discount_amount'] else "N/A"
                    
                    print(f"{status} {offer['restaurant_name']}: '{offer['offer_name']}'")
                    print(f"   - Discount %: {discount_pct}")
                    print(f"   - Discount €: {discount_amt}")
                    print(f"   - Type: {offer['offer_type']}")
                    print(f"   - Products: {offer['product_count']}")
                    print()
                
                # Summary stats
                active_offers = [o for o in offers if o['is_active']]
                percentage_offers = [o for o in offers if o['discount_percentage'] and o['discount_percentage'] > 0]
                
                print(f"📋 Summary:")
                print(f"   ✅ Active offers: {len(active_offers)}")
                print(f"   📊 Offers with % discount: {len(percentage_offers)}")
                print(f"   💰 Total products with offers: {sum(o['product_count'] for o in offers)}")
                
                if percentage_offers:
                    avg_discount = sum(o['discount_percentage'] for o in percentage_offers) / len(percentage_offers)
                    print(f"   📈 Average discount: {avg_discount:.1f}%")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
