#!/usr/bin/env python3
"""
Import Logic Patch Tool
======================

This tool applies the duplicate prevention fix to the import_data.py file.
It replaces the _ensure_product method with the improved version.
"""

import os
from pathlib import Path

def create_patch():
    """Create a patch for the import_data.py file."""
    
    # Read the original file
    import_file = Path(__file__).parent.parent / 'database' / 'import_data.py'
    
    with open(import_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # The new _ensure_product method (improved version)
    new_ensure_product = '''    def _ensure_product(self, cur, restaurant_id: str, category_mapping: Dict[str, str],
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
                    self.logger.info(f"Product name changed: '{result['name']}' → '{product_name}' (external_id: {external_id})")
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
                    self.logger.info(f"Updating external_id: '{existing_external_id}' → '{external_id}' for product '{product_name}'")
                    cur.execute("UPDATE products SET external_id = %s, updated_at = NOW() WHERE id = %s",
                               (external_id, existing_product['id']))
                elif external_id and not existing_external_id:
                    # Same name, existing has NULL external_id - set external_id
                    self.logger.info(f"Setting external_id: NULL → '{external_id}' for product '{product_name}'")
                    cur.execute("UPDATE products SET external_id = %s, updated_at = NOW() WHERE id = %s",
                               (external_id, existing_product['id']))
                
                return existing_product['id']
            else:
                # Multiple products with same name - this should not happen with proper uniqueness
                self.logger.warning(f"Found {len(existing_by_name)} products with name '{product_name}' - using first one")
                return existing_by_name[0]['id']
        
        # Step 3: No existing product found - create new one
        product_id = str(uuid.uuid4())
        options = product_data.get('options', [])
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except:
                options = []
        
        self.logger.info(f"Creating new product: '{product_name}' (external_id: {external_id})")
        
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
        
        return product_id'''
    
    # Find and replace the _ensure_product method
    import re
    
    # Pattern to match the entire _ensure_product method
    pattern = r'(\s+def _ensure_product\(self, cur, restaurant_id: str, category_mapping: Dict\[str, str\],\s+product_data: Dict\[str, Any\]\) -> str:.*?)(\n\s+def _create_restaurant_snapshot)'
    
    # Find the method
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        # Replace the method
        updated_content = content[:match.start(1)] + new_ensure_product + match.group(2)
        
        # Create backup
        backup_file = import_file.with_suffix('.py.backup')
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Write updated content
        with open(import_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"✅ Successfully patched {import_file}")
        print(f"📁 Backup created at {backup_file}")
        print("\n🔧 CHANGES MADE:")
        print("1. Added name-based lookup to prevent duplicates")
        print("2. Added external_id update capability")
        print("3. Added product name update capability")
        print("4. Added comprehensive logging")
        print("5. Enhanced error handling for multiple matches")
        
        return True
    else:
        print("❌ Could not find _ensure_product method to patch")
        return False

if __name__ == "__main__":
    print("🔧 Applying Import Logic Patch")
    print("=" * 30)
    
    success = create_patch()
    
    if success:
        print("\n✅ PATCH APPLIED SUCCESSFULLY!")
        print("\n📝 NEXT STEPS:")
        print("1. Test the patched import logic")
        print("2. Monitor logs during next scrape")
        print("3. Verify no new duplicates are created")
        print("4. Run validation scripts to confirm")
    else:
        print("\n❌ PATCH FAILED!")
        print("Manual intervention required.")
