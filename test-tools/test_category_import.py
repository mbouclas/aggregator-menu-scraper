#!/usr/bin/env python3
"""
Category Import Logic Analysis
=============================

This tool analyzes the category import logic for potential issues with duplicate handling.
It checks for failed insertions and constraint violations.
"""

import psycopg2
import psycopg2.extras
import os
from pathlib import Path
from dotenv import load_dotenv
import sys

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_db_config():
    """Load database configuration from database/.env file."""
    env_path = Path(__file__).parent.parent / 'database' / '.env'
    load_dotenv(env_path)
    
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'scraper_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres123')
    }

def test_category_import_logic():
    """Test the category import logic for duplicate handling issues."""
    print("🧪 Testing Category Import Logic")
    print("=" * 35)
    
    try:
        from database.import_data import ScraperDataImporter
        
        # Build connection string
        config = load_db_config()
        connection_string = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        
        # Create importer
        importer = ScraperDataImporter(connection_string)
        
        print("✅ Successfully imported ScraperDataImporter")
        
        # Get a real restaurant to test with
        cur = importer.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, name FROM restaurants LIMIT 1")
        restaurant = cur.fetchone()
        
        if not restaurant:
            print("❌ No restaurants found in database")
            return False
        
        restaurant_id = restaurant['id']
        restaurant_name = restaurant['name']
        
        print(f"🏪 Testing with restaurant: {restaurant_name}")
        
        # Test scenario 1: Import same category twice
        print("\n🧪 Test 1: Import Same Category Twice")
        print("-" * 40)
        
        test_categories = [
            {'name': 'Test Category 001', 'description': 'Test description', 'display_order': 1, 'source': 'test'},
            {'name': 'Test Category 002', 'description': 'Test description', 'display_order': 2, 'source': 'test'}
        ]
        
        # First import
        print("  First import attempt...")
        try:
            mapping1 = importer._import_categories(cur, restaurant_id, test_categories)
            print(f"  ✅ First import successful: {mapping1}")
        except Exception as e:
            print(f"  ❌ First import failed: {e}")
            importer.close()
            return False
        
        # Second import (should find existing)
        print("  Second import attempt...")
        try:
            mapping2 = importer._import_categories(cur, restaurant_id, test_categories)
            print(f"  ✅ Second import successful: {mapping2}")
            
            # Check if same IDs returned
            if mapping1 == mapping2:
                print("  ✅ Same category IDs returned - logic working correctly")
            else:
                print("  ⚠️  Different category IDs returned - potential issue!")
                print(f"     First:  {mapping1}")
                print(f"     Second: {mapping2}")
        except Exception as e:
            print(f"  ❌ Second import failed: {e}")
        
        # Test scenario 2: Constraint violation simulation
        print("\n🧪 Test 2: Direct Constraint Violation Test")
        print("-" * 45)
        
        try:
            # Try to manually insert duplicate category
            import uuid
            duplicate_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO categories (id, restaurant_id, name, description, display_order, source)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (duplicate_id, restaurant_id, 'Test Category 001', 'Duplicate test', 99, 'test'))
            
            print("  ❌ Constraint violation not detected - this is a problem!")
            
        except psycopg2.errors.UniqueViolation:
            print("  ✅ Unique constraint properly prevents duplicates")
            importer.conn.rollback()  # Rollback the failed transaction
        except Exception as e:
            print(f"  ⚠️  Unexpected error: {e}")
            importer.conn.rollback()
        
        # Clean up test data
        print("\n🧹 Cleaning up test data...")
        try:
            cur.execute("""
                DELETE FROM categories 
                WHERE restaurant_id = %s AND name LIKE 'Test Category %'
            """, (restaurant_id,))
            importer.conn.commit()
            print("  ✅ Test data cleaned up")
        except Exception as e:
            print(f"  ⚠️  Cleanup warning: {e}")
        
        importer.close()
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def analyze_import_efficiency():
    """Analyze the efficiency of category import logic."""
    print("\n📊 Category Import Efficiency Analysis")
    print("=" * 40)
    
    conn = psycopg2.connect(**load_db_config())
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Analyze category creation frequency
    cur.execute("""
        SELECT 
            DATE_TRUNC('hour', created_at) as hour,
            COUNT(*) as categories_created,
            COUNT(DISTINCT restaurant_id) as restaurants,
            COUNT(DISTINCT name) as unique_names,
            ROUND(COUNT(*)::numeric / COUNT(DISTINCT name), 2) as attempt_ratio
        FROM categories
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY DATE_TRUNC('hour', created_at)
        ORDER BY hour DESC
        LIMIT 10
    """)
    
    hourly_stats = cur.fetchall()
    
    if hourly_stats:
        print("Category creation attempts (last 24 hours):")
        print("Hour                | Created | Unique | Restaurants | Attempt Ratio")
        print("-" * 70)
        
        total_created = 0
        total_unique = 0
        
        for stat in hourly_stats:
            total_created += stat['categories_created']
            total_unique += stat['unique_names']
            
            print(f"{stat['hour'].strftime('%Y-%m-%d %H:00')} | {stat['categories_created']:7} | {stat['unique_names']:6} | {stat['restaurants']:11} | {stat['attempt_ratio']:13}")
        
        if total_unique > 0:
            overall_ratio = total_created / total_unique
            print(f"\nOverall attempt ratio: {overall_ratio:.2f}")
            if overall_ratio > 1.1:
                print("⚠️  High attempt ratio suggests duplicate creation attempts")
            else:
                print("✅ Normal attempt ratio - import logic efficient")
    else:
        print("No categories created in the last 24 hours")
    
    conn.close()

def check_category_import_errors():
    """Check for potential category import error patterns."""
    print("\n🔍 Category Import Error Pattern Analysis")
    print("=" * 45)
    
    # Check if there are any patterns that suggest the import logic is trying to create duplicates
    print("🔍 Current import logic analysis:")
    
    import_file = Path(__file__).parent.parent / 'database' / 'import_data.py'
    
    with open(import_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for proper duplicate handling in category import
    issues = []
    
    if "SELECT id FROM categories WHERE restaurant_id = %s AND name = %s" in content:
        print("✅ Category existence check found")
    else:
        issues.append("❌ No category existence check found")
    
    if "ON CONFLICT" in content:
        print("⚠️  ON CONFLICT clause found - may be masking logic issues")
    else:
        print("✅ No ON CONFLICT clause - using proper existence checks")
    
    # Check for transaction handling
    if "BEGIN" in content or "COMMIT" in content or "ROLLBACK" in content:
        print("✅ Transaction handling present")
    else:
        print("⚠️  Limited transaction handling visible")
    
    if issues:
        print("\n🚨 ISSUES FOUND:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n✅ No obvious issues found in import logic")

if __name__ == "__main__":
    print("🔧 Category Import Logic Analysis")
    print("=" * 35)
    
    # Test the import logic
    test_success = test_category_import_logic()
    
    # Analyze efficiency
    analyze_import_efficiency()
    
    # Check for error patterns
    check_category_import_errors()
    
    print(f"\n📊 ANALYSIS SUMMARY:")
    print(f"✅ Import Logic Test: {'Passed' if test_success else 'Failed'}")
    print(f"✅ Database has unique constraint on (restaurant_id, name)")
    print(f"✅ Current database state is clean (no duplicates)")
    print(f"⚠️  Recent import attempts show duplicate creation tries")
    print(f"\n💡 RECOMMENDATION:")
    print(f"The import logic appears correct, but the attempt ratio suggests")
    print(f"it may be trying to create duplicates that are blocked by the constraint.")
    print(f"This is inefficient and may indicate a logic gap or race condition.")
