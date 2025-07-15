#!/usr/bin/env python3
"""
Offer Management Utilities
==========================
Simple utilities for managing and monitoring offers in the database.

Usage:
    python offer_utils.py list-offers
    python offer_utils.py active-offers  
    python offer_utils.py offer-stats
"""

import psycopg2
import psycopg2.extras
import argparse
import logging
from datetime import datetime, timedelta
from import_data import load_db_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class OfferManager:
    """Utility class for managing offers in the database."""
    
    def __init__(self, connection_string: str):
        """Initialize with database connection."""
        try:
            self.conn = psycopg2.connect(connection_string)
            logger.info("Connected to PostgreSQL database")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def list_offers(self, restaurant_name=None):
        """List all offers, optionally filtered by restaurant."""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            query = """
                SELECT 
                    o.id,
                    o.name as offer_name,
                    r.name as restaurant_name,
                    r.brand as restaurant_brand,
                    o.offer_type,
                    o.discount_percentage,
                    o.start_date,
                    o.end_date,
                    o.is_active,
                    o.created_at,
                    COUNT(pp.id) as products_affected
                FROM offers o
                JOIN restaurants r ON o.restaurant_id = r.id
                LEFT JOIN product_prices pp ON o.id = pp.offer_id
                WHERE 1=1
            """
            params = []
            
            if restaurant_name:
                query += " AND r.name ILIKE %s"
                params.append(f"%{restaurant_name}%")
            
            query += """
                GROUP BY o.id, r.name, r.brand
                ORDER BY o.created_at DESC
            """
            
            cur.execute(query, params)
            return cur.fetchall()
    
    def get_active_offers(self):
        """Get all currently active offers."""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    o.name as offer_name,
                    r.name as restaurant_name,
                    r.brand as restaurant_brand,
                    o.offer_type,
                    o.discount_percentage,
                    o.start_date,
                    o.end_date,
                    COUNT(pp.id) as products_affected,
                    MIN(pp.scraped_at) as first_seen,
                    MAX(pp.scraped_at) as last_seen
                FROM offers o
                JOIN restaurants r ON o.restaurant_id = r.id
                LEFT JOIN product_prices pp ON o.id = pp.offer_id
                WHERE o.is_active = true
                    AND (o.start_date IS NULL OR o.start_date <= NOW())
                    AND (o.end_date IS NULL OR o.end_date >= NOW())
                GROUP BY o.id, o.name, r.name, r.brand, o.offer_type, o.discount_percentage, o.start_date, o.end_date
                ORDER BY products_affected DESC
            """)
            return cur.fetchall()
    
    def get_offer_statistics(self):
        """Get overall offer statistics."""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Total offers
            cur.execute("SELECT COUNT(*) as total_offers FROM offers")
            result = cur.fetchone()
            total_offers = result['total_offers'] if result else 0
            
            # Active offers
            cur.execute("""
                SELECT COUNT(*) as active_offers 
                FROM offers 
                WHERE is_active = true 
                    AND (start_date IS NULL OR start_date <= NOW())
                    AND (end_date IS NULL OR end_date >= NOW())
            """)
            result = cur.fetchone()
            active_offers = result['active_offers'] if result else 0
            
            # Restaurants with offers
            cur.execute("""
                SELECT COUNT(DISTINCT restaurant_id) as restaurants_with_offers 
                FROM offers 
                WHERE is_active = true
            """)
            result = cur.fetchone()
            restaurants_with_offers = result['restaurants_with_offers'] if result else 0
            
            # Products affected by offers
            cur.execute("""
                SELECT COUNT(DISTINCT pp.product_id) as products_with_offers
                FROM product_prices pp
                WHERE pp.offer_id IS NOT NULL
            """)
            result = cur.fetchone()
            products_with_offers = result['products_with_offers'] if result else 0
            
            # Average discount percentage
            cur.execute("""
                SELECT AVG(discount_percentage) as avg_discount
                FROM offers 
                WHERE is_active = true AND discount_percentage > 0
            """)
            result = cur.fetchone()
            avg_discount = result['avg_discount'] if result and result['avg_discount'] else 0
            
            return {
                'total_offers': total_offers,
                'active_offers': active_offers,
                'restaurants_with_offers': restaurants_with_offers,
                'products_with_offers': products_with_offers,
                'avg_discount_percentage': round(float(avg_discount), 2)
            }
    
    def cleanup_inactive_offers(self, days_old: int = 30):
        """Mark offers as inactive if they haven't been seen in recent scrapes."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        with self.conn.cursor() as cur:
            # Find offers that haven't been seen in recent product_prices
            cur.execute("""
                UPDATE offers 
                SET is_active = false, updated_at = NOW()
                WHERE is_active = true
                    AND id NOT IN (
                        SELECT DISTINCT offer_id 
                        FROM product_prices 
                        WHERE offer_id IS NOT NULL 
                            AND scraped_at >= %s
                    )
            """, (cutoff_date,))
            
            deactivated_count = cur.rowcount
            self.conn.commit()
            
            logger.info(f"Deactivated {deactivated_count} offers not seen in last {days_old} days")
            return deactivated_count

def print_offers_simple(offers):
    """Print offers in simple format."""
    if not offers:
        print("No offers found.")
        return
    
    print(f"\n🎁 Found {len(offers)} offers:")
    print("=" * 80)
    
    for offer in offers:
        status = "Active" if offer.get('is_active', True) else "Inactive"
        if offer.get('end_date') and offer['end_date'] < datetime.now():
            status = "Expired"
        
        print(f"🏪 {offer.get('restaurant_name', '')}")
        print(f"   Offer: {offer.get('offer_name', '')}")
        print(f"   Discount: {offer.get('discount_percentage', 0) or 0}%")
        print(f"   Products: {offer.get('products_affected', 0)}")
        print(f"   Status: {status}")
        if offer.get('created_at'):
            print(f"   Created: {offer['created_at'].strftime('%Y-%m-%d %H:%M')}")
        print("-" * 40)

def print_statistics(stats):
    """Print offer statistics."""
    print(f"\n📊 Offer Statistics")
    print("=" * 50)
    print(f"🎁 Total Offers:              {stats['total_offers']:,}")
    print(f"✅ Active Offers:             {stats['active_offers']:,}")
    print(f"🏪 Restaurants with Offers:   {stats['restaurants_with_offers']:,}")
    print(f"🛍️  Products with Offers:      {stats['products_with_offers']:,}")
    print(f"💰 Average Discount:          {stats['avg_discount_percentage']}%")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Offer management utilities')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List offers command
    list_parser = subparsers.add_parser('list-offers', help='List all offers')
    list_parser.add_argument('--restaurant', help='Filter by restaurant name')
    
    # Active offers command
    subparsers.add_parser('active-offers', help='Show currently active offers')
    
    # Statistics command
    subparsers.add_parser('offer-stats', help='Show offer statistics')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup-inactive', help='Cleanup inactive offers')
    cleanup_parser.add_argument('--days', type=int, default=30, 
                               help='Mark offers inactive if not seen for this many days')
    
    parser.add_argument('--connection', help='PostgreSQL connection string')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get connection string
    if args.connection:
        connection_string = args.connection
    else:
        try:
            connection_string = load_db_config()
        except Exception as e:
            logger.error(f"Failed to load database configuration: {e}")
            return
    
    # Execute command
    manager = None
    try:
        manager = OfferManager(connection_string)
        
        if args.command == 'list-offers':
            offers = manager.list_offers(getattr(args, 'restaurant', None))
            print_offers_simple(offers)
            
        elif args.command == 'active-offers':
            offers = manager.get_active_offers()
            print_offers_simple(offers)
            
        elif args.command == 'offer-stats':
            stats = manager.get_offer_statistics()
            print_statistics(stats)
            
        elif args.command == 'cleanup-inactive':
            count = manager.cleanup_inactive_offers(getattr(args, 'days', 30))
            print(f"✅ Deactivated {count} inactive offers")
                
    except Exception as e:
        logger.error(f"Command failed: {e}")
    finally:
        if manager:
            manager.close()

if __name__ == '__main__':
    main()
