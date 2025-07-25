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
            logger.info(f"Successfully imported {file_path} (session: {session_id})")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to import {file_path}: {e}")
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
                
                # 6. Extract and import offers
                offer_mapping = self._import_offers(cur, restaurant_id, products_data, metadata['scraped_at'])
                
                # 7. Import products and prices (with offer links)
                product_count = self._import_products_and_prices(
                    cur, restaurant_id, category_mapping, products_data, metadata['scraped_at'], offer_mapping
                )
                
                # 8. Create restaurant snapshot
                self._create_restaurant_snapshot(cur, restaurant_id, domain_id, restaurant_data, metadata)
                
                # 9. Update session with final counts
                errors = json_data.get('errors', [])
                self._update_scraping_session(cur, session_id, product_count, len(categories_data), len(errors), errors)
                
                self.conn.commit()
                logger.info(f"Imported {product_count} products in {len(categories_data)} categories")
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
        """
        Import categories and return name to ID mapping.
        Optimized version that reduces duplicate creation attempts.
        """
        category_mapping = {}
        
        if not categories_data:
            logger.debug("No categories data provided")
            categories_data = []
        
        # Extract all category names (including 'Uncategorized')
        category_names = [cat_data['name'] for cat_data in categories_data]
        if 'Uncategorized' not in category_names:
            category_names.append('Uncategorized')
        
        # Batch fetch existing categories for this restaurant
        logger.debug(f"Checking existing categories for restaurant {restaurant_id}")
        
        if category_names:
            # Use ANY to efficiently check multiple names at once
            cur.execute("""
                SELECT name, id FROM categories 
                WHERE restaurant_id = %s AND name = ANY(%s)
            """, (restaurant_id, category_names))
            
            existing_categories = {row['name']: row['id'] for row in cur.fetchall()}
            logger.debug(f"Found {len(existing_categories)} existing categories")
        else:
            existing_categories = {}
        
        # Process each category
        categories_to_create = []
        
        for cat_data in categories_data:
            cat_name = cat_data['name']
            
            if cat_name in existing_categories:
                # Category already exists
                category_mapping[cat_name] = existing_categories[cat_name]
                logger.debug(f"Using existing category: {cat_name}")
            else:
                # Need to create this category
                category_id = str(uuid.uuid4())
                categories_to_create.append({
                    'id': category_id,
                    'restaurant_id': restaurant_id,
                    'name': cat_name,
                    'description': cat_data.get('description', ''),
                    'display_order': cat_data.get('display_order', 0),
                    'source': cat_data.get('source', 'scraper')
                })
                category_mapping[cat_name] = category_id
        
        # Handle 'Uncategorized' category
        if 'Uncategorized' not in existing_categories:
            uncategorized_id = str(uuid.uuid4())
            categories_to_create.append({
                'id': uncategorized_id,
                'restaurant_id': restaurant_id,
                'name': 'Uncategorized',
                'description': 'Products without specific category',
                'display_order': 999,
                'source': 'fallback'
            })
            category_mapping['Uncategorized'] = uncategorized_id
        else:
            category_mapping['Uncategorized'] = existing_categories['Uncategorized']
        
        # Batch create new categories using ON CONFLICT for safety
        if categories_to_create:
            logger.info(f"Creating {len(categories_to_create)} new categories")
            
            for cat in categories_to_create:
                try:
                    cur.execute("""
                        INSERT INTO categories (id, restaurant_id, name, description, display_order, source)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (restaurant_id, name) DO NOTHING
                    """, (
                        cat['id'], cat['restaurant_id'], cat['name'],
                        cat['description'], cat['display_order'], cat['source']
                    ))
                    
                    # Check if the insert actually happened or if there was a conflict
                    if cur.rowcount == 0:
                        # Conflict occurred, get the existing ID
                        logger.warning(f"Category '{cat['name']}' already exists (conflict), fetching existing ID")
                        cur.execute("""
                            SELECT id FROM categories 
                            WHERE restaurant_id = %s AND name = %s
                        """, (cat['restaurant_id'], cat['name']))
                        result = cur.fetchone()
                        if result:
                            category_mapping[cat['name']] = result['id']
                        else:
                            logger.error(f"Failed to find existing category '{cat['name']}' after conflict")
                    else:
                        logger.debug(f"Successfully created category: {cat['name']}")
                        
                except psycopg2.Error as e:
                    logger.error(f"Error creating category '{cat['name']}': {e}")
                    # Try to get existing category as fallback
                    try:
                        cur.execute("""
                            SELECT id FROM categories 
                            WHERE restaurant_id = %s AND name = %s
                        """, (cat['restaurant_id'], cat['name']))
                        result = cur.fetchone()
                        if result:
                            category_mapping[cat['name']] = result['id']
                            logger.warning(f"Using existing category after error: {cat['name']}")
                    except psycopg2.Error:
                        logger.error(f"Could not recover from category creation error for '{cat['name']}'")
                        raise
        
        logger.debug(f"Processed {len(category_mapping)} categories")
        return category_mapping

    def _import_offers(self, cur, restaurant_id: str, products_data: list, scraped_at: str) -> Dict[str, str]:
        """Extract unique offers from products and create offer records. Returns offer_name -> offer_id mapping."""
        offers_seen = set()
        offer_mapping = {}  # offer_name -> offer_id
        active_offers = set()  # Track which offers have active products in current scrape
        
        # First pass: collect all offers that should be active based on current scrape
        for product in products_data:
            offer_name = product.get('offer_name', '').strip()
            discount_pct = float(product.get('discount_percentage', 0))
            price = float(product.get('price', 0))
            original_price = float(product.get('original_price', 0))
            
            # An offer is considered active if:
            # 1. There's an explicit offer_name, OR
            # 2. There's a discount_percentage > 0 AND (price < original_price OR price == original_price)
            #    Note: When price == original_price but discount_pct > 0, we'll calculate the true original
            
            # Pattern 1: Explicit offer name
            if offer_name:
                active_offers.add(offer_name)
                if offer_name not in offers_seen:
                    offers_seen.add(offer_name)
            
            # Pattern 2: Discount percentage without offer name (auto-generate offer name)
            elif discount_pct > 0:
                auto_offer_name = f"{int(discount_pct)}% Discount"
                active_offers.add(auto_offer_name)
                if auto_offer_name not in offers_seen:
                    offers_seen.add(auto_offer_name)
        
        # Second pass: Deactivate offers that are no longer active
        self._deactivate_inactive_offers(cur, restaurant_id, active_offers, scraped_at)
        
        # Third pass: Ensure all active offers exist
        for offer_name in offers_seen:
            # Find the discount percentage for this offer
            discount_pct = 0
            for product in products_data:
                product_offer_name = product.get('offer_name', '').strip()
                product_discount_pct = float(product.get('discount_percentage', 0))
                
                if product_offer_name == offer_name:
                    discount_pct = product_discount_pct
                    break
                elif not product_offer_name and product_discount_pct > 0:
                    auto_offer_name = f"{int(product_discount_pct)}% Discount"
                    if auto_offer_name == offer_name:
                        discount_pct = product_discount_pct
                        break
            
            offer_id = self._ensure_offer(
                cur=cur,
                restaurant_id=restaurant_id,
                offer_name=offer_name,
                discount_percentage=discount_pct,
                scraped_at=scraped_at
            )
            offer_mapping[offer_name] = offer_id
                
        logger.debug(f"Processed {len(offer_mapping)} unique offers, deactivated inactive offers")
        return offer_mapping
    
    def _deactivate_inactive_offers(self, cur, restaurant_id: str, active_offers: set, scraped_at: str):
        """Deactivate offers that are no longer active in the current scrape."""
        
        # Get all currently active offers for this restaurant
        cur.execute("""
            SELECT id, name FROM offers 
            WHERE restaurant_id = %s AND is_active = true
        """, (restaurant_id,))
        
        current_active_offers = cur.fetchall()
        
        for offer_row in current_active_offers:
            offer_name = offer_row['name']
            offer_id = offer_row['id']
            
            # If this offer is not in the current scrape's active offers, deactivate it
            if offer_name not in active_offers:
                # Check if this offer actually has no active products
                # An offer is inactive if all products with this offer have price == original_price
                # and discount_percentage = 0 in the current scrape
                
                should_deactivate = self._should_deactivate_offer(cur, offer_id, restaurant_id, scraped_at)
                
                if should_deactivate:
                    cur.execute("""
                        UPDATE offers 
                        SET is_active = false, end_date = %s, updated_at = %s
                        WHERE id = %s
                    """, (scraped_at, scraped_at, offer_id))
                    
                    logger.info(f"Deactivated offer '{offer_name}' for restaurant {restaurant_id}")
    
    def _should_deactivate_offer(self, cur, offer_id: str, restaurant_id: str, scraped_at: str) -> bool:
        """Check if an offer should be deactivated based on current product pricing."""
        
        # Get all products that were previously linked to this offer
        cur.execute("""
            SELECT DISTINCT p.id, p.name, pp.scraped_at
            FROM products p
            JOIN product_prices pp ON p.id = pp.product_id
            WHERE p.restaurant_id = %s 
              AND pp.offer_id = %s
              AND pp.scraped_at < %s
            ORDER BY p.id, pp.scraped_at DESC
        """, (restaurant_id, offer_id, scraped_at))
        
        previously_linked_products = cur.fetchall()
        
        if not previously_linked_products:
            # No products were ever linked to this offer, safe to deactivate
            return True
        
        # Check if any of these products still have active discounts in the current scrape
        # This is a complex check that would require access to the current products_data
        # For now, we'll be conservative and only deactivate if explicitly told
        # In a full implementation, you'd pass the current products_data to this method
        
        # For this implementation, we'll deactivate offers that no longer appear in the current scrape
        return True
    
    def _ensure_offer(self, cur, restaurant_id: str, offer_name: str, 
                     discount_percentage: float, scraped_at: str) -> str:
        """Ensure offer exists and return its ID. Reactivates previously deactivated offers if needed."""
        
        # First check if there's an active offer with this name
        cur.execute("""
            SELECT id FROM offers 
            WHERE restaurant_id = %s AND name = %s AND is_active = true
        """, (restaurant_id, offer_name))
        
        existing_active = cur.fetchone()
        if existing_active:
            return existing_active['id']
        
        # Check if there's an inactive offer with this name that we can reactivate
        cur.execute("""
            SELECT id, discount_percentage FROM offers 
            WHERE restaurant_id = %s AND name = %s AND is_active = false
            ORDER BY created_at DESC
            LIMIT 1
        """, (restaurant_id, offer_name))
        
        existing_inactive = cur.fetchone()
        if existing_inactive:
            # Reactivate the existing offer
            offer_id = existing_inactive['id']
            
            # Update the offer with current discount percentage and reactivate
            cur.execute("""
                UPDATE offers 
                SET is_active = true, 
                    end_date = NULL, 
                    discount_percentage = %s,
                    updated_at = %s,
                    start_date = %s
                WHERE id = %s
            """, (
                discount_percentage if discount_percentage > 0 else None,
                scraped_at,
                scraped_at,  # New start_date when reactivated
                offer_id
            ))
            
            logger.info(f"Reactivated offer '{offer_name}' ({discount_percentage}%) for restaurant {restaurant_id}")
            return offer_id
        
        # Create new offer if none exists
        offer_id = str(uuid.uuid4())
        
        # Determine offer type and discount amount based on discount percentage
        if discount_percentage > 0:
            offer_type = 'percentage'
            # Note: discount_amount will be calculated per product since it depends on individual prices
            discount_amount = None
        else:
            offer_type = 'other'
            discount_amount = None
        
        cur.execute("""
            INSERT INTO offers (
                id, restaurant_id, name, offer_type, discount_percentage, 
                discount_amount, start_date, is_active, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            offer_id,
            restaurant_id,
            offer_name,
            offer_type,
            discount_percentage if discount_percentage > 0 else None,
            discount_amount,  # Individual amounts calculated per product
            scraped_at,  # Use first seen as start_date
            True,
            scraped_at
        ))
        
        logger.debug(f"Created new offer: {offer_name} ({discount_percentage}% discount)")
        return offer_id
    
    def _import_products_and_prices(self, cur, restaurant_id: str, category_mapping: Dict[str, str],
                                  products_data: list, scraped_at: str, offer_mapping: Optional[Dict[str, str]] = None) -> int:
        """Import products and their current prices, linking to offers where applicable."""
        if offer_mapping is None:
            offer_mapping = {}
            
        imported_count = 0
        
        for product_data in products_data:
            # Skip products without required fields
            if not product_data.get('name') or not product_data.get('id'):
                logger.warning(f"Skipping product with missing name or ID: {product_data}")
                continue
            
            try:
                # Get or create product
                product_id = self._ensure_product(cur, restaurant_id, category_mapping, product_data)
                
                # Get offer_id for product (handle both explicit and auto-generated offers)
                offer_name = product_data.get('offer_name', '').strip()
                discount_pct = float(product_data.get('discount_percentage', 0))
                offer_id = None
                final_offer_name = None
                
                if offer_name:
                    # Explicit offer name
                    offer_id = offer_mapping.get(offer_name)
                    final_offer_name = offer_name
                elif discount_pct > 0:
                    # Auto-generated offer name
                    auto_offer_name = f"{int(discount_pct)}% Discount"
                    offer_id = offer_mapping.get(auto_offer_name)
                    final_offer_name = auto_offer_name
                
                # Calculate correct original price if discount exists but original_price = price
                price = float(product_data.get('price', 0))
                original_price = float(product_data.get('original_price', 0))
                
                # Fix original price calculation when price = original but discount exists
                if discount_pct > 0 and price == original_price:
                    # Calculate what original price should be: price = original * (1 - discount/100)
                    # So: original = price / (1 - discount/100)
                    calculated_original = price / (1 - discount_pct/100)
                    original_price = round(calculated_original, 2)
                    logger.debug(f"Corrected original price for {product_data.get('name', 'unknown')}: "
                               f"€{price} -> €{original_price} ({discount_pct}% discount)")
                
                # Calculate discount amount
                discount_amount = original_price - price if original_price > price else None
                
                # Add price record with offer link and corrected calculations
                cur.execute("""
                    INSERT INTO product_prices (
                        product_id, price, original_price, currency, discount_percentage,
                        offer_id, offer_name, availability, scraped_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (product_id, scraped_at) DO NOTHING
                """, (
                    product_id,
                    price,
                    original_price,  # Use corrected original price
                    product_data.get('currency', 'EUR'),
                    discount_pct,
                    offer_id,  # Link to offer record (explicit or auto-generated)
                    final_offer_name,  # Use final offer name (explicit or auto-generated)
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
        """
        Ensure product exists and return its ID.
        Enhanced version that prevents duplicates by checking product names.
        """
        external_id = product_data['id']
        product_name = product_data['name']
        category_name = product_data.get('category', 'Uncategorized')
        category_id = category_mapping.get(category_name, category_mapping.get('Uncategorized'))
        
        if not category_id:
            raise ValueError(f"Category '{category_name}' not found and no Uncategorized fallback")
        
        # Step 1: Try to find by external_id (if provided)
        if external_id:
            cur.execute("SELECT id, name FROM products WHERE restaurant_id = %s AND external_id = %s", 
                       (restaurant_id, external_id))
            result = cur.fetchone()
            
            if result:
                # Found by external_id, check if name changed
                if result['name'] != product_name:
                    logger.info(f"Product name changed: '{result['name']}' → '{product_name}' (external_id: {external_id})")
                    # Update the name
                    cur.execute("UPDATE products SET name = %s, updated_at = NOW() WHERE id = %s",
                               (product_name, result['id']))
                return result['id']
        
        # Step 2: Check for existing product with same name (prevent duplicates)
        cur.execute("SELECT id, external_id FROM products WHERE restaurant_id = %s AND name = %s", 
                   (restaurant_id, product_name))
        existing_by_name = cur.fetchall()
        
        if existing_by_name:
            # Found product(s) with same name
            if len(existing_by_name) == 1:
                existing_product = existing_by_name[0]
                existing_external_id = existing_product['external_id']
                
                if external_id and existing_external_id and existing_external_id != external_id:
                    # Same name, different external_id - update external_id
                    logger.info(f"Updating external_id: '{existing_external_id}' → '{external_id}' for product '{product_name}'")
                    cur.execute("UPDATE products SET external_id = %s, updated_at = NOW() WHERE id = %s",
                               (external_id, existing_product['id']))
                elif external_id and not existing_external_id:
                    # Same name, existing has NULL external_id - set external_id
                    logger.info(f"Setting external_id: NULL → '{external_id}' for product '{product_name}'")
                    cur.execute("UPDATE products SET external_id = %s, updated_at = NOW() WHERE id = %s",
                               (external_id, existing_product['id']))
                
                return existing_product['id']
            else:
                # Multiple products with same name - this should not happen with proper uniqueness
                logger.warning(f"Found {len(existing_by_name)} products with name '{product_name}' - using first one")
                return existing_by_name[0]['id']
        
        # Step 3: No existing product found - create new one
        product_id = str(uuid.uuid4())
        options = product_data.get('options', [])
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except:
                options = []
        
        logger.info(f"Creating new product: '{product_name}' (external_id: {external_id})")
        
        cur.execute("""
            INSERT INTO products (
                id, restaurant_id, category_id, external_id, name, description,
                image_url, options
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            product_id, restaurant_id, category_id, external_id,
            product_name, 
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
            print(f"Successfully imported {args.file}")
            print(f"📋 Session ID: {session_id}")
        
        elif args.directory:
            session_ids = importer.import_directory(args.directory)
            print(f"Successfully imported {len(session_ids)} files")
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
