#!/usr/bin/env python3
"""
Database Setup Script
====================
Creates the database and initializes the schema for the scraper project.
"""

import psycopg2
import psycopg2.extensions
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def load_db_config():
    """Load database configuration from .env file."""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded environment from {env_path}")
    else:
        logger.error(f"No .env file found at {env_path}")
        sys.exit(1)
    
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'scraper_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '')
    }

def create_database():
    """Create the database if it doesn't exist."""
    config = load_db_config()
    
    # Connect to postgres database to create our target database
    try:
        # Connect to the default 'postgres' database first
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database='postgres',  # Connect to default database
            user=config['user'],
            password=config['password']
        )
        conn.autocommit = True
        
        with conn.cursor() as cur:
            # Check if database exists
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (config['database'],))
            if cur.fetchone():
                logger.info(f"Database '{config['database']}' already exists")
            else:
                # Create database
                cur.execute(f"CREATE DATABASE {config['database']}")
                logger.info(f"✅ Created database '{config['database']}'")
        
        conn.close()
        return True
        
    except psycopg2.Error as e:
        logger.error(f"Failed to create database: {e}")
        return False

def initialize_schema():
    """Initialize the database schema."""
    config = load_db_config()
    
    try:
        # Connect to our target database
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        
        # Read and execute schema file
        schema_file = Path(__file__).parent / 'init_schema.sql'
        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file}")
            return False
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Database schema initialized successfully")
        return True
        
    except psycopg2.Error as e:
        logger.error(f"Failed to initialize schema: {e}")
        return False
    except Exception as e:
        logger.error(f"Error reading schema file: {e}")
        return False

def test_connection():
    """Test the database connection and show table count."""
    config = load_db_config()
    
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        
        with conn.cursor() as cur:
            # Count tables
            cur.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            table_count = cur.fetchone()[0]
            
            # Count views
            cur.execute("""
                SELECT COUNT(*) 
                FROM information_schema.views 
                WHERE table_schema = 'public'
            """)
            view_count = cur.fetchone()[0]
        
        conn.close()
        
        logger.info(f"✅ Connection successful")
        logger.info(f"📊 Found {table_count} tables and {view_count} views")
        return True
        
    except psycopg2.Error as e:
        logger.error(f"Connection test failed: {e}")
        return False

def main():
    """Main setup process."""
    logger.info("🚀 Starting database setup...")
    
    # Step 1: Create database
    if not create_database():
        logger.error("❌ Database creation failed")
        sys.exit(1)
    
    # Step 2: Initialize schema
    if not initialize_schema():
        logger.error("❌ Schema initialization failed")
        sys.exit(1)
    
    # Step 3: Test connection
    if not test_connection():
        logger.error("❌ Connection test failed")
        sys.exit(1)
    
    logger.info("🎉 Database setup completed successfully!")
    logger.info("You can now run: python database/import_data.py --directory output/")

if __name__ == '__main__':
    main()
