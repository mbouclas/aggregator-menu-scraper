#!/usr/bin/env python3
"""
Clean Up Offers Table
=====================
Remove offers with null discount_amount and discount_percentage values.
"""

import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    """Clean up the offers table by removing null discount records."""
    
    conn_string = (
        f"host={os.getenv('DB_HOST', 'localhost')} "
        f"dbname={os.getenv('DB_NAME', 'scraper_db')} "
        f"user={os.getenv('DB_USER', 'postgres')} "
        f"password={os.getenv('DB_PASSWORD', 'postgres123')}"
    )
    
    print("🧹 Cleaning Up Offers Table")
    print("=" * 50)
    
    try:
        with psycopg2.connect(conn_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                
                # First, let's see what we have
                print("📊 Current Offers Table Status:")
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_offers,
                        COUNT(CASE WHEN discount_percentage IS NULL AND discount_amount IS NULL THEN 1 END) as null_discount_offers,
                        COUNT(CASE WHEN discount_percentage IS NOT NULL OR discount_amount IS NOT NULL THEN 1 END) as valid_offers,
                        COUNT(CASE WHEN offer_type = 'other' THEN 1 END) as other_type_offers
                    FROM offers;
                """)
                
                stats = cur.fetchone()
                if not stats:
                    print("❌ No data found in offers table")
                    return
                    
                print(f"   📋 Total offers: {stats['total_offers']}")
                print(f"   ❌ NULL discount offers: {stats['null_discount_offers']}")
                print(f"   ✅ Valid offers: {stats['valid_offers']}")
                print(f"   🏷️  'Other' type offers: {stats['other_type_offers']}")
                
                # Show examples of problematic offers
                print(f"\n🔍 Examples of Problematic Offers:")
                cur.execute("""
                    SELECT r.name as restaurant_name, o.name as offer_name, 
                           o.discount_percentage, o.discount_amount, o.offer_type,
                           o.is_active
                    FROM offers o
                    JOIN restaurants r ON o.restaurant_id = r.id
                    WHERE o.discount_percentage IS NULL AND o.discount_amount IS NULL
                    ORDER BY r.name, o.name
                    LIMIT 10;
                """)
                
                problematic = cur.fetchall()
                for offer in problematic:
                    status = "ACTIVE" if offer['is_active'] else "INACTIVE"
                    print(f"   • {offer['restaurant_name']}: '{offer['offer_name']}' "
                          f"(Type: {offer['offer_type']}, Status: {status})")
                
                if stats['null_discount_offers'] == 0:
                    print(f"\n✅ No cleanup needed! All offers have valid discount data.")
                    return
                
                # Ask for confirmation
                print(f"\n⚠️  Warning: About to delete {stats['null_discount_offers']} offers with NULL discount values.")
                print(f"   This will also remove any product_prices records linked to these offers.")
                
                # Show which offers will be deleted
                print(f"\n📋 Offers to be deleted:")
                cur.execute("""
                    SELECT r.name as restaurant_name, o.name as offer_name, 
                           o.is_active, o.created_at,
                           COUNT(pp.id) as linked_products
                    FROM offers o
                    JOIN restaurants r ON o.restaurant_id = r.id
                    LEFT JOIN product_prices pp ON pp.offer_id = o.id
                    WHERE o.discount_percentage IS NULL AND o.discount_amount IS NULL
                    GROUP BY o.id, r.name, o.name, o.is_active, o.created_at
                    ORDER BY r.name, o.name;
                """)
                
                to_delete = cur.fetchall()
                for offer in to_delete:
                    status = "ACTIVE" if offer['is_active'] else "INACTIVE"
                    print(f"   • {offer['restaurant_name']}: '{offer['offer_name']}' "
                          f"({status}, {offer['linked_products']} products, Created: {offer['created_at'].date()})")
                
                response = input(f"\n❓ Continue with deletion? (y/N): ").strip().lower()
                if response != 'y':
                    print("❌ Cleanup cancelled.")
                    return
                
                # Perform the cleanup
                print(f"\n🧹 Starting cleanup...")
                
                # First, remove product_prices linked to these offers
                cur.execute("""
                    DELETE FROM product_prices 
                    WHERE offer_id IN (
                        SELECT id FROM offers 
                        WHERE discount_percentage IS NULL AND discount_amount IS NULL
                    );
                """)
                deleted_prices = cur.rowcount
                print(f"   🗑️  Deleted {deleted_prices} product_prices records")
                
                # Then, delete the offers themselves
                cur.execute("""
                    DELETE FROM offers 
                    WHERE discount_percentage IS NULL AND discount_amount IS NULL;
                """)
                deleted_offers = cur.rowcount
                print(f"   🗑️  Deleted {deleted_offers} offers")
                
                # Commit the transaction
                conn.commit()
                
                # Show final status
                print(f"\n✅ Cleanup Complete!")
                cur.execute("SELECT COUNT(*) as remaining FROM offers;")
                result = cur.fetchone()
                remaining = result['remaining'] if result else 0
                print(f"   📊 Remaining offers: {remaining}")
                
                # Verify no NULL discount offers remain
                cur.execute("""
                    SELECT COUNT(*) as null_count 
                    FROM offers 
                    WHERE discount_percentage IS NULL AND discount_amount IS NULL;
                """)
                result = cur.fetchone()
                null_count = result['null_count'] if result else 0
                
                if null_count == 0:
                    print(f"   ✅ All NULL discount offers successfully removed!")
                else:
                    print(f"   ⚠️  Warning: {null_count} NULL discount offers still remain")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
