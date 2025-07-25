#!/usr/bin/env python3
"""
Script to check the database after import to see if categories are properly assigned.
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

def check_categories():
    """Check if Coffee Island products have proper categories assigned."""
    connection_string = get_connection_string()
    
    try:
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                
                # First, check what tables exist
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                tables = [row['table_name'] for row in cur.fetchall()]
                print("=== AVAILABLE TABLES ===")
                for table in tables:
                    print(f"- {table}")
                
                # Check Coffee Island categories
                print("\n=== COFFEE ISLAND CATEGORIES IN DATABASE ===")
                cur.execute("""
                    SELECT c.name, COUNT(p.id) as product_count
                    FROM categories c 
                    JOIN restaurants r ON c.restaurant_id = r.id
                    LEFT JOIN products p ON c.id = p.category_id
                    WHERE r.name = 'Coffee Island'
                    GROUP BY c.id, c.name
                    ORDER BY c.name
                """)
                categories = cur.fetchall()
                
                for cat in categories:
                    print(f"- '{cat['name']}': {cat['product_count']} products")
                
                # Check specific products and their categories
                print("\n=== SAMPLE COFFEE ISLAND PRODUCTS AND CATEGORIES ===")
                cur.execute("""
                    SELECT p.name as product_name, c.name as category_name
                    FROM products p
                    JOIN categories c ON p.category_id = c.id
                    JOIN restaurants r ON p.restaurant_id = r.id
                    WHERE r.name = 'Coffee Island'
                    ORDER BY p.name
                    LIMIT 10
                """)
                products = cur.fetchall()
                
                for prod in products:
                    print(f"- '{prod['product_name']}' -> '{prod['category_name']}'")
                
                # Check if any products are uncategorized
                print("\n=== UNCATEGORIZED PRODUCTS COUNT ===")
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM products p
                    JOIN categories c ON p.category_id = c.id
                    JOIN restaurants r ON p.restaurant_id = r.id
                    WHERE r.name = 'Coffee Island' AND c.name = 'Uncategorized'
                """)
                uncategorized_count = cur.fetchone()['count']
                print(f"Uncategorized products: {uncategorized_count}")
                
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise

if __name__ == "__main__":
    check_categories()
