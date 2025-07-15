#!/usr/bin/env python3
"""
Migrate Existing Offers
=======================
This script processes existing JSON files and extracts offers to populate the offers table.
Use this to migrate historical data after implementing offer import logic.

Usage:
    python migrate_existing_offers.py --directory ../output/
    python migrate_existing_offers.py --file ../output/foody_costa-coffee.json
"""

import os
import json
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv
from import_data import ScraperDataImporter, load_db_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def migrate_existing_json_files(directory_path: str, connection_string: str):
    """Process existing JSON files to extract and import offers."""
    directory = Path(directory_path)
    json_files = list(directory.glob("*.json"))
    
    if not json_files:
        logger.warning(f"No JSON files found in {directory_path}")
        return
    
    logger.info(f"Found {len(json_files)} JSON files to process")
    
    # Connect to database
    importer = None
    try:
        importer = ScraperDataImporter(connection_string)
        
        processed_count = 0
        offers_created = 0
        
        for json_file in json_files:
            logger.info(f"Processing {json_file.name}...")
            
            try:
                # Re-import the file (this will now include offer processing)
                session_id = importer.import_json_file(str(json_file))
                processed_count += 1
                logger.info(f"✅ Successfully processed {json_file.name} (session: {session_id})")
                
            except Exception as e:
                logger.error(f"❌ Failed to process {json_file.name}: {e}")
                continue
        
        logger.info(f"🎉 Migration completed! Processed {processed_count}/{len(json_files)} files")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        if importer:
            importer.close()

def migrate_single_file(file_path: str, connection_string: str):
    """Process a single JSON file to extract and import offers."""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return
    
    logger.info(f"Processing file: {file_path}")
    
    importer = None
    try:
        importer = ScraperDataImporter(connection_string)
        session_id = importer.import_json_file(file_path)
        logger.info(f"✅ Successfully processed {file_path} (session: {session_id})")
        
    except Exception as e:
        logger.error(f"❌ Failed to process {file_path}: {e}")
        raise
    finally:
        if importer:
            importer.close()

def analyze_offers_in_json(file_path: str):
    """Analyze what offers exist in a JSON file without importing."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    restaurant_name = data['restaurant']['name']
    products = data.get('products', [])
    
    offers_found = {}
    products_with_offers = 0
    
    for product in products:
        offer_name = product.get('offer_name', '').strip()
        discount_pct = product.get('discount_percentage', 0)
        
        if offer_name:
            if offer_name not in offers_found:
                offers_found[offer_name] = {
                    'discount_percentage': discount_pct,
                    'product_count': 0
                }
            offers_found[offer_name]['product_count'] += 1
            products_with_offers += 1
    
    print(f"\n📊 Offer Analysis for {restaurant_name}")
    print(f"📁 File: {file_path}")
    print(f"🛍️  Total products: {len(products)}")
    print(f"🎁 Products with offers: {products_with_offers}")
    print(f"🏷️  Unique offers found: {len(offers_found)}")
    
    if offers_found:
        print(f"\n🎯 Offer Details:")
        for offer_name, details in offers_found.items():
            print(f"   • {offer_name}")
            print(f"     - Discount: {details['discount_percentage']}%")
            print(f"     - Products: {details['product_count']}")
    else:
        print("   No offers found in this file")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Migrate existing offer data from JSON files')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', help='Process a single JSON file')
    group.add_argument('--directory', help='Process all JSON files in directory')
    
    parser.add_argument('--connection', 
                       help='PostgreSQL connection string (default: load from .env)')
    
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only analyze offers without importing (works with --file only)')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle analyze-only mode
    if args.analyze_only:
        if not args.file:
            logger.error("--analyze-only can only be used with --file")
            return
        analyze_offers_in_json(args.file)
        return
    
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
            return
    
    # Process files
    try:
        if args.file:
            migrate_single_file(args.file, connection_string)
        elif args.directory:
            migrate_existing_json_files(args.directory, connection_string)
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")

if __name__ == '__main__':
    main()
