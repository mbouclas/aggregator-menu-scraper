#!/usr/bin/env python3
"""
Script to clean up Coffee Island data and re-import properly.
"""
import os
import psycopg2
import psycopg2.extras
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

def get_connection_string():
    """Get database connection string from environment."""
    # Load .env from database directory specifically
    env_path = Path(__file__).parent / 'database' / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded environment from {env_path}")
    else:
        logger.error(f"No .env file found at {env_path}")
        return None
    
    # Check if we have a pre-built connection string
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url
    
    # Build from components
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'scraper_db')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    if db_password:
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        return f"postgresql://{db_user}@{db_host}:{db_port}/{db_name}"

def cleanup_coffee_island():
    """Clean up Coffee Island data to remove old corrupted imports."""
    connection_string = get_connection_string()
    
    try:
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                
                # Get Coffee Island restaurant ID
                cur.execute("SELECT id FROM restaurants WHERE name = 'Coffee Island'")
                restaurant = cur.fetchone()
                if not restaurant:
                    logger.error("Coffee Island restaurant not found")
                    return
                
                restaurant_id = restaurant['id']
                logger.info(f"Found Coffee Island restaurant ID: {restaurant_id}")
                
                # Count current data
                cur.execute("SELECT COUNT(*) FROM products WHERE restaurant_id = %s", (restaurant_id,))
                product_count = cur.fetchone()['count']
                
                cur.execute("SELECT COUNT(*) FROM categories WHERE restaurant_id = %s", (restaurant_id,))
                category_count = cur.fetchone()['count']
                
                logger.info(f"Current Coffee Island data: {product_count} products, {category_count} categories")
                
                # Delete all Coffee Island data
                logger.info("Deleting Coffee Island product prices...")
                cur.execute("""
                    DELETE FROM product_prices 
                    WHERE product_id IN (
                        SELECT id FROM products WHERE restaurant_id = %s
                    )
                """, (restaurant_id,))
                
                logger.info("Deleting Coffee Island products...")
                cur.execute("DELETE FROM products WHERE restaurant_id = %s", (restaurant_id,))
                
                logger.info("Deleting Coffee Island categories...")
                cur.execute("DELETE FROM categories WHERE restaurant_id = %s", (restaurant_id,))
                
                logger.info("Deleting Coffee Island snapshots...")
                cur.execute("DELETE FROM restaurant_snapshots WHERE restaurant_id = %s", (restaurant_id,))
                
                # Commit the changes
                conn.commit()
                logger.info("Coffee Island data cleanup completed successfully")
                
    except Exception as e:
        logger.error(f"Database error during cleanup: {e}")
        raise

if __name__ == "__main__":
    cleanup_coffee_island()
