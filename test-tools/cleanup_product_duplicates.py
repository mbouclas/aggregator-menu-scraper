#!/usr/bin/env python3
"""
Product Duplicate Cleanup Script
Merges duplicate products within each restaurant and updates all related records.
"""

import psycopg2
import psycopg2.extras
from typing import Dict, List, Tuple, Set, Any
import logging
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from database directory
env_path = Path(__file__).parent / 'database' / '.env'
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'product_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def connect_to_db():
    """Connect to PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'scraper_db'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres123')
        )
        logger.info("Connected to database")
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def get_exact_duplicates(conn) -> List[Dict]:
    """Get all exact product name duplicates within restaurants."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        query = """
        SELECT 
            p.restaurant_id,
            r.name as restaurant_name,
            p.name,
            ARRAY_AGG(p.id ORDER BY p.created_at) as product_ids,
            COUNT(*) as duplicate_count
        FROM products p
        JOIN restaurants r ON p.restaurant_id = r.id
        GROUP BY p.restaurant_id, r.name, p.name
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC, r.name, p.name;
        """
        cur.execute(query)
        return cur.fetchall()

def get_product_dependencies(conn, product_id: str) -> Dict:
    """Get all records that depend on a product."""
    dependencies = {
        'offers': [],
        'prices': []
    }
    
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # Get offers (but offers don't directly reference products, they reference restaurants)
        # For now, we'll just track product_prices
        
        # Get prices 
        cur.execute("SELECT id FROM product_prices WHERE product_id = %s", (product_id,))
        dependencies['prices'] = [row['id'] for row in cur.fetchall()]
    
    return dependencies

def merge_products(conn, keep_product_id: str, merge_product_ids: List[str]) -> Dict:
    """Merge duplicate products into the kept product."""
    stats = {
        'offers_updated': 0,
        'prices_updated': 0,
        'prices_deleted': 0,
        'products_deleted': 0
    }
    
    with conn.cursor() as cur:
        for product_id in merge_product_ids:
            # Handle product_prices with potential conflicts
            # First, try to update prices that won't conflict
            cur.execute("""
                UPDATE product_prices 
                SET product_id = %s 
                WHERE product_id = %s
                AND NOT EXISTS (
                    SELECT 1 FROM product_prices pp2 
                    WHERE pp2.product_id = %s 
                    AND pp2.scraped_at = product_prices.scraped_at
                )
            """, (keep_product_id, product_id, keep_product_id))
            stats['prices_updated'] += cur.rowcount
            
            # Delete conflicting prices (keep the ones already on the target product)
            cur.execute("""
                DELETE FROM product_prices 
                WHERE product_id = %s
                AND EXISTS (
                    SELECT 1 FROM product_prices pp2 
                    WHERE pp2.product_id = %s 
                    AND pp2.scraped_at = product_prices.scraped_at
                )
            """, (product_id, keep_product_id))
            stats['prices_deleted'] += cur.rowcount
            
            # Delete the duplicate product
            cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
            stats['products_deleted'] += cur.rowcount
            
            logger.info(f"   🔄 Merged {product_id} into {keep_product_id}")
    
    return stats

def cleanup_exact_duplicates(conn):
    """Clean up all exact product name duplicates."""
    logger.info("Starting exact duplicate cleanup...")
    
    duplicates = get_exact_duplicates(conn)
    total_stats = {
        'restaurants_affected': 0,
        'duplicate_groups': 0,
        'offers_updated': 0,
        'prices_updated': 0,
        'prices_deleted': 0,
        'products_deleted': 0
    }
    
    current_restaurant = None
    
    for duplicate in duplicates:
        restaurant_name = duplicate['restaurant_name']
        product_name = duplicate['name']
        product_ids = duplicate['product_ids']
        count = duplicate['duplicate_count']
        
        if current_restaurant != restaurant_name:
            current_restaurant = restaurant_name
            total_stats['restaurants_affected'] += 1
            logger.info(f"\nProcessing: {restaurant_name}")
        
        logger.info(f"   Merging '{product_name}' ({count} duplicates)")
        
        # Parse the PostgreSQL array string format {id1,id2,id3}
        product_ids_str = product_ids.strip('{}')
        product_ids_list = [pid.strip() for pid in product_ids_str.split(',') if pid.strip()]
        
        if len(product_ids_list) <= 1:
            continue
        
        # Keep the oldest product (first in the sorted array)
        keep_product_id = product_ids_list[0]
        merge_product_ids = product_ids_list[1:]
        
        # Merge the duplicates
        merge_stats = merge_products(conn, keep_product_id, merge_product_ids)
        
        # Update totals
        total_stats['duplicate_groups'] += 1
        total_stats['offers_updated'] += merge_stats['offers_updated']
        total_stats['prices_updated'] += merge_stats['prices_updated'] 
        total_stats['prices_deleted'] += merge_stats['prices_deleted']
        total_stats['products_deleted'] += merge_stats['products_deleted']
        
        logger.info(f"   Kept {keep_product_id}, merged {len(merge_product_ids)} duplicates")
    
    return total_stats

def cleanup_external_id_conflicts(conn):
    """Clean up products with conflicting external IDs."""
    logger.info("\n🔧 Starting external ID conflict cleanup...")
    
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # Find products with same external_id but different product_ids within same restaurant
        query = """
        SELECT 
            p.restaurant_id,
            r.name as restaurant_name,
            p.external_id,
            p.name,
            ARRAY_AGG(p.id ORDER BY p.created_at) as product_ids,
            COUNT(*) as conflict_count
        FROM products p
        JOIN restaurants r ON p.restaurant_id = r.id
        WHERE p.external_id IS NOT NULL
        GROUP BY p.restaurant_id, r.name, p.external_id, p.name
        HAVING COUNT(*) > 1
        ORDER BY conflict_count DESC, r.name, p.external_id;
        """
        cur.execute(query)
        conflicts = cur.fetchall()
    
    stats = {
        'conflicts_resolved': 0,
        'products_deleted': 0
    }
    
    for conflict in conflicts:
        restaurant_name = conflict['restaurant_name']
        external_id = conflict['external_id']
        product_name = conflict['name']
        product_ids = conflict['product_ids']
        
        logger.info(f"🔧 Resolving external ID conflict: {restaurant_name} - {external_id} - {product_name}")
        
        # Parse the PostgreSQL array string format {id1,id2,id3}
        product_ids_str = product_ids.strip('{}')
        product_ids_list = [pid.strip() for pid in product_ids_str.split(',') if pid.strip()]
        
        if len(product_ids_list) <= 1:
            continue
        
        # Keep first product, merge others
        keep_product_id = product_ids_list[0]
        merge_product_ids = product_ids_list[1:]
        
        merge_stats = merge_products(conn, keep_product_id, merge_product_ids)
        stats['conflicts_resolved'] += 1
        stats['products_deleted'] += merge_stats['products_deleted']
    
    return stats

def verify_cleanup_results(conn):
    """Verify the cleanup was successful."""
    logger.info("\n📊 Verifying cleanup results...")
    
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # Check for remaining exact duplicates
        cur.execute("""
            SELECT COUNT(*) as remaining_exact_duplicates
            FROM (
                SELECT restaurant_id, name, COUNT(*)
                FROM products
                GROUP BY restaurant_id, name
                HAVING COUNT(*) > 1
            ) t;
        """)
        exact_remaining = cur.fetchone()['remaining_exact_duplicates']
        
        # Check for remaining external ID conflicts
        cur.execute("""
            SELECT COUNT(*) as remaining_external_conflicts  
            FROM (
                SELECT restaurant_id, external_id, COUNT(*)
                FROM products
                WHERE external_id IS NOT NULL
                GROUP BY restaurant_id, external_id
                HAVING COUNT(*) > 1
            ) t;
        """)
        external_remaining = cur.fetchone()['remaining_external_conflicts']
        
        # Get final product count
        cur.execute("SELECT COUNT(*) as total_products FROM products")
        total_products = cur.fetchone()['total_products']
        
        logger.info(f"   📦 Total products after cleanup: {total_products}")
        logger.info(f"   🔍 Remaining exact duplicates: {exact_remaining}")
        logger.info(f"   🔗 Remaining external ID conflicts: {external_remaining}")
        
        return {
            'total_products': total_products,
            'exact_duplicates_remaining': exact_remaining,
            'external_conflicts_remaining': external_remaining
        }

def main():
    """Main cleanup process."""
    logger.info("Starting Product Duplicate Cleanup")
    logger.info("=" * 60)
    
    conn = None
    try:
        conn = connect_to_db()
        conn.autocommit = False  # Use transactions
        
        # Start transaction
        with conn:
            # Clean up exact duplicates
            exact_stats = cleanup_exact_duplicates(conn)
            
            # Clean up external ID conflicts  
            external_stats = cleanup_external_id_conflicts(conn)
            
            # Verify results
            verification = verify_cleanup_results(conn)
            
            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("CLEANUP SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Restaurants affected: {exact_stats['restaurants_affected']}")
            logger.info(f"Duplicate groups merged: {exact_stats['duplicate_groups']}")
            logger.info(f"External ID conflicts resolved: {external_stats['conflicts_resolved']}")
            logger.info(f"Offers updated: {exact_stats['offers_updated']}")
            logger.info(f"Prices updated: {exact_stats['prices_updated']}")
            logger.info(f"Products deleted: {exact_stats['products_deleted'] + external_stats['products_deleted']}")
            logger.info(f"Final product count: {verification['total_products']}")
            
            if verification['exact_duplicates_remaining'] == 0 and verification['external_conflicts_remaining'] == 0:
                logger.info("SUCCESS: All duplicates cleaned up!")
            else:
                logger.warning(f"Some issues remain: {verification['exact_duplicates_remaining']} exact + {verification['external_conflicts_remaining']} external")
            
            # Commit the transaction
            logger.info("\nCommitting changes...")
            
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Cleanup failed: {e}")
        raise
    finally:
        if conn:
            conn.close()
        logger.info("Database connection closed")

if __name__ == "__main__":
    main()
