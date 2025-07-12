#!/usr/bin/env python3
"""
Scraper Data Importer
=====================
Import scraper JSON output files into PostgreSQL database.

Usage:
    python import_data.py --file output/foody_costa-coffee.json
    python import_data.py --directory output/
    python import_data.py --file output/wolt_kfc-engomi.json --connection "postgresql://user:pass@localhost/scraper_db"
"""

import json
import psycopg2
import psycopg2.extras
import argparse
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def load_db_config() -> str:
    """Load database configuration from .env file and return connection string."""
    # Load environment variables from .env file
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.debug(f"Loaded environment from {env_path}")
    else:
        logger.warning(f"No .env file found at {env_path}")
    
    # Get database configuration from environment variables
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'scraper_db')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    # Check if we have a pre-built connection string
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url
    
    # Build connection string from individual components
    if db_password:
        connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        connection_string = f"postgresql://{db_user}@{db_host}:{db_port}/{db_name}"
    
    logger.debug(f"Built connection string for {db_host}:{db_port}/{db_name}")
    return connection_string

class ScraperDataImporter:
    """Import scraper JSON data into PostgreSQL database."""
    
    def __init__(self, connection_string: str):
        """Initialize importer with database connection."""
        try:
            self.conn = psycopg2.connect(connection_string)
            self.conn.autocommit = False
            logger.info("Connected to PostgreSQL database")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def import_json_file(self, file_path: str) -> str:
        """Import a single JSON file and return session ID."""
        logger.info(f"Importing file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            session_id = self.import_scraper_data(data)
            logger.info(f"✅ Successfully imported {file_path} (session: {session_id})")
            return session_id
            
        except Exception as e:
            logger.error(f"❌ Failed to import {file_path}: {e}")
            raise
    
    def import_directory(self, directory_path: str) -> List[str]:
        """Import all JSON files in a directory."""
        directory = Path(directory_path)
        json_files = list(directory.glob("*.json"))
        
        if not json_files:
            logger.warning(f"No JSON files found in {directory_path}")
            return []
        
        session_ids = []
        for json_file in json_files:
            try:
                session_id = self.import_json_file(str(json_file))
                session_ids.append(session_id)
            except Exception as e:
                logger.error(f"Skipping {json_file} due to error: {e}")
                continue
        
        logger.info(f"Imported {len(session_ids)} files out of {len(json_files)} total")
        return session_ids
    
    def import_scraper_data(self, json_data: Dict[str, Any]) -> str:
        """Import a complete scraper JSON output into the database."""
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Extract basic info
                metadata = json_data['metadata']
                source = json_data['source']
                restaurant_data = json_data['restaurant']
                categories_data = json_data['categories']
                products_data = json_data['products']
                
                logger.info(f"Processing {restaurant_data['name']} from {metadata['domain']}")
                
                # 1. Ensure domain exists
                domain_id = self._ensure_domain(cur, metadata['domain'])
                
                # 1.5. Get scraper_id for this domain
                scraper_id = self._get_scraper_id_for_domain(cur, metadata['domain'])
                
                # 2. Ensure restaurant exists
                restaurant_id = self._ensure_restaurant(cur, restaurant_data)
                
                # 3. Link restaurant to domain
                self._ensure_restaurant_domain(cur, restaurant_id, domain_id, source['url'], restaurant_data['name'])
                
                # 4. Create scraping session
                session_id = self._create_scraping_session(cur, restaurant_id, domain_id, scraper_id, metadata, source)
                
                # 5. Import categories
                category_mapping = self._import_categories(cur, restaurant_id, categories_data)
                
                # 6. Import products and prices
                product_count = self._import_products_and_prices(
                    cur, restaurant_id, category_mapping, products_data, metadata['scraped_at']
                )
                
                # 7. Create restaurant snapshot
                self._create_restaurant_snapshot(cur, restaurant_id, domain_id, restaurant_data, metadata)
                
                # 8. Update session with final counts
                errors = json_data.get('errors', [])
                self._update_scraping_session(cur, session_id, product_count, len(categories_data), len(errors), errors)
                
                self.conn.commit()
                logger.info(f"✅ Imported {product_count} products in {len(categories_data)} categories")
                return str(session_id)
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Import failed, rolled back transaction: {e}")
            raise e
    
    def _get_scraper_id_for_domain(self, cur, domain_name: str) -> str:
        """Determine scraper_id based on domain name."""
        # Map domains to scrapers
        if 'foody' in domain_name.lower():
            scraper_name = 'foody'
        elif 'wolt' in domain_name.lower():
            scraper_name = 'wolt'
        else:
            # Default fallback - could be enhanced to detect from URL patterns
            scraper_name = 'foody'  # Default to foody for unknown domains
            
        cur.execute("SELECT id FROM scrapers WHERE name = %s", (scraper_name,))
        result = cur.fetchone()
        
        if result:
            return result['id']
        else:
            logger.error(f"No scraper found with name: {scraper_name}")
            raise ValueError(f"Scraper '{scraper_name}' not found in database")

    def _ensure_domain(self, cur, domain_name: str) -> str:
        """Ensure domain exists and return its ID."""
        cur.execute("SELECT id FROM domains WHERE name = %s", (domain_name,))
        result = cur.fetchone()
        
        if result:
            return result['id']
        
        # Get scraper_id for this domain
        scraper_id = self._get_scraper_id_for_domain(cur, domain_name)
        
        domain_id = str(uuid.uuid4())
        display_name = domain_name.replace('.com', '').replace('.cy', '').title()
        
        cur.execute("""
            INSERT INTO domains (id, name, display_name, base_url, scraper_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (domain_id, domain_name, display_name, f"https://{domain_name}", scraper_id))
        
        logger.debug(f"Created new domain: {domain_name}")
        return domain_id
    
    def _ensure_restaurant(self, cur, restaurant_data: Dict[str, Any]) -> str:
        """Ensure restaurant exists and return its ID."""
        name = restaurant_data['name']
        brand = restaurant_data.get('brand', name) or name
        
        # Create slug from name
        slug = name.lower()
        slug = slug.replace(' ', '-').replace('&', 'and').replace("'", '')
        slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
        slug = slug.strip('-')
        
        cur.execute("SELECT id FROM restaurants WHERE name = %s AND brand = %s", (name, brand))
        result = cur.fetchone()
        
        if result:
            return result['id']
        
        restaurant_id = str(uuid.uuid4())
        cuisine_types = restaurant_data.get('cuisine_types', [])
        if isinstance(cuisine_types, str):
            cuisine_types = [cuisine_types] if cuisine_types else []
        
        cur.execute("""
            INSERT INTO restaurants (id, name, brand, slug, address, phone, cuisine_types)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            restaurant_id, name, brand, slug,
            restaurant_data.get('address') or '',
            restaurant_data.get('phone') or '',
            cuisine_types
        ))
        
        logger.debug(f"Created new restaurant: {name}")
        return restaurant_id
    
    def _ensure_restaurant_domain(self, cur, restaurant_id: str, domain_id: str, url: str, domain_specific_name: str):
        """Link restaurant to domain."""
        cur.execute("""
            INSERT INTO restaurant_domains (restaurant_id, domain_id, domain_url, domain_specific_name, last_seen_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (restaurant_id, domain_id) 
            DO UPDATE SET 
                domain_url = EXCLUDED.domain_url, 
                domain_specific_name = EXCLUDED.domain_specific_name,
                last_seen_at = NOW()
        """, (restaurant_id, domain_id, url, domain_specific_name))
    
    def _create_scraping_session(self, cur, restaurant_id: str, domain_id: str, scraper_id: str,
                               metadata: Dict[str, Any], source: Dict[str, Any]) -> str:
        """Create a new scraping session record."""
        session_id = str(uuid.uuid4())
        
        # Parse timestamps
        started_at = metadata['scraped_at']
        completed_at = metadata.get('processed_at')
        duration = metadata.get('processing_duration_seconds')
        
        cur.execute("""
            INSERT INTO scraping_sessions (
                id, scraper_id, restaurant_id, domain_id, scraper_version, scraping_method,
                url, started_at, completed_at, duration_seconds, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            session_id, scraper_id, restaurant_id, domain_id,
            metadata.get('scraper_version', '1.0.0'),
            metadata.get('scraping_method', 'unknown'),
            source['url'],
            started_at,
            completed_at,
            duration,
            'completed'
        ))
        
        return session_id
    
    def _import_categories(self, cur, restaurant_id: str, categories_data: list) -> Dict[str, str]:
        """Import categories and return name to ID mapping."""
        category_mapping = {}
        
        for cat_data in categories_data:
            cat_name = cat_data['name']
            
            # Check if category exists
            cur.execute("SELECT id FROM categories WHERE restaurant_id = %s AND name = %s", 
                       (restaurant_id, cat_name))
            result = cur.fetchone()
            
            if result:
                category_mapping[cat_name] = result['id']
                continue
            
            # Create new category
            category_id = str(uuid.uuid4())
            
            cur.execute("""
                INSERT INTO categories (id, restaurant_id, name, description, display_order, source)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                category_id, restaurant_id, cat_name,
                cat_data.get('description', ''),
                cat_data.get('display_order', 0),
                cat_data.get('source', 'unknown')
            ))
            
            category_mapping[cat_name] = category_id
        
        # Add "Uncategorized" if not present
        if 'Uncategorized' not in category_mapping:
            cur.execute("SELECT id FROM categories WHERE restaurant_id = %s AND name = %s", 
                       (restaurant_id, 'Uncategorized'))
            result = cur.fetchone()
            
            if not result:
                uncategorized_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO categories (id, restaurant_id, name, description, display_order, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (uncategorized_id, restaurant_id, 'Uncategorized', 'Products without specific category', 999, 'fallback'))
                category_mapping['Uncategorized'] = uncategorized_id
            else:
                category_mapping['Uncategorized'] = result['id']
        
        logger.debug(f"Processed {len(category_mapping)} categories")
        return category_mapping
    
    def _import_products_and_prices(self, cur, restaurant_id: str, category_mapping: Dict[str, str],
                                  products_data: list, scraped_at: str) -> int:
        """Import products and their current prices."""
        imported_count = 0
        
        for product_data in products_data:
            # Skip products without required fields
            if not product_data.get('name') or not product_data.get('id'):
                logger.warning(f"Skipping product with missing name or ID: {product_data}")
                continue
            
            try:
                # Get or create product
                product_id = self._ensure_product(cur, restaurant_id, category_mapping, product_data)
                
                # Add price record
                cur.execute("""
                    INSERT INTO product_prices (
                        product_id, price, original_price, currency, discount_percentage,
                        offer_name, availability, scraped_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (product_id, scraped_at) DO NOTHING
                """, (
                    product_id,
                    float(product_data.get('price', 0)),
                    float(product_data.get('original_price', 0)),
                    product_data.get('currency', 'EUR'),
                    float(product_data.get('discount_percentage', 0)),
                    product_data.get('offer_name'),  # Future field
                    product_data.get('availability', True),
                    scraped_at
                ))
                
                imported_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to import product {product_data.get('name', 'unknown')}: {e}")
                continue
        
        return imported_count
    
    def _ensure_product(self, cur, restaurant_id: str, category_mapping: Dict[str, str],
                       product_data: Dict[str, Any]) -> str:
        """Ensure product exists and return its ID."""
        external_id = product_data['id']
        category_name = product_data.get('category', 'Uncategorized')
        category_id = category_mapping.get(category_name, category_mapping.get('Uncategorized'))
        
        if not category_id:
            raise ValueError(f"Category '{category_name}' not found and no Uncategorized fallback")
        
        cur.execute("SELECT id FROM products WHERE restaurant_id = %s AND external_id = %s", 
                   (restaurant_id, external_id))
        result = cur.fetchone()
        
        if result:
            return result['id']
        
        product_id = str(uuid.uuid4())
        options = product_data.get('options', [])
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except:
                options = []
        
        cur.execute("""
            INSERT INTO products (
                id, restaurant_id, category_id, external_id, name, description,
                image_url, options
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            product_id, restaurant_id, category_id, external_id,
            product_data['name'], 
            product_data.get('description', ''),
            product_data.get('image_url', ''),
            json.dumps(options)
        ))
        
        return product_id
    
    def _create_restaurant_snapshot(self, cur, restaurant_id: str, domain_id: str,
                                  restaurant_data: Dict[str, Any], metadata: Dict[str, Any]):
        """Create a restaurant snapshot for this scrape."""
        cur.execute("""
            INSERT INTO restaurant_snapshots (
                restaurant_id, domain_id, rating, delivery_fee, minimum_order,
                delivery_time, total_products, total_categories, scraped_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (restaurant_id, domain_id, scraped_at) DO NOTHING
        """, (
            restaurant_id, domain_id,
            float(restaurant_data.get('rating', 0)) if restaurant_data.get('rating') else None,
            float(restaurant_data.get('delivery_fee', 0)) if restaurant_data.get('delivery_fee') else None,
            float(restaurant_data.get('minimum_order', 0)) if restaurant_data.get('minimum_order') else None,
            restaurant_data.get('delivery_time', ''),
            metadata.get('product_count', 0),
            metadata.get('category_count', 0),
            metadata['scraped_at']
        ))
    
    def _update_scraping_session(self, cur, session_id: str, product_count: int, 
                               category_count: int, error_count: int, errors: list):
        """Update scraping session with final counts."""
        cur.execute("""
            UPDATE scraping_sessions 
            SET product_count = %s, category_count = %s, error_count = %s, errors = %s
            WHERE id = %s
        """, (product_count, category_count, error_count, json.dumps(errors), session_id))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Import scraper JSON data into PostgreSQL')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', help='Import a single JSON file')
    group.add_argument('--directory', help='Import all JSON files in directory')
    
    parser.add_argument('--connection', 
                       help='PostgreSQL connection string (default: load from .env file)')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get connection string
    if args.connection:
        connection_string = args.connection
        logger.info("Using connection string from command line")
    else:
        try:
            connection_string = load_db_config()
            logger.info("Using connection string from .env file")
        except Exception as e:
            logger.error(f"Failed to load database configuration: {e}")
            logger.error("Please provide --connection argument or create a .env file")
            sys.exit(1)
    
    # Validate inputs
    if args.file and not os.path.exists(args.file):
        logger.error(f"File not found: {args.file}")
        sys.exit(1)
    
    if args.directory and not os.path.exists(args.directory):
        logger.error(f"Directory not found: {args.directory}")
        sys.exit(1)
    
    # Import data
    importer = None
    try:
        importer = ScraperDataImporter(connection_string)
        
        if args.file:
            session_id = importer.import_json_file(args.file)
            print(f"✅ Successfully imported {args.file}")
            print(f"📋 Session ID: {session_id}")
        
        elif args.directory:
            session_ids = importer.import_directory(args.directory)
            print(f"✅ Successfully imported {len(session_ids)} files")
            print(f"📋 Session IDs: {', '.join(session_ids[:5])}" + 
                  (f" (and {len(session_ids)-5} more)" if len(session_ids) > 5 else ""))
    
    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)
    
    finally:
        if importer:
            importer.close()


if __name__ == '__main__':
    main()
