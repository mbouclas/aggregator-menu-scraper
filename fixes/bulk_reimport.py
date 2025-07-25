#!/usr/bin/env python3
"""
Bulk re-import script to import clean data for all restaurants that have output files.
This script should be run after bulk_cleanup.py to restore clean category data.
"""
import sys
import os
import subprocess
import glob

def find_all_output_files():
    """Find all available output files for re-import"""
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    
    # Get all JSON files in output directory
    json_files = glob.glob(os.path.join(output_dir, '*.json'))
    
    # Filter out files that look like test files or backups
    valid_files = []
    for file_path in json_files:
        filename = os.path.basename(file_path)
        if not any(skip in filename.lower() for skip in ['modified', 'backup', 'test', 'unknown']):
            valid_files.append(file_path)
    
    return valid_files

def run_import(file_path):
    """Run the import_data.py script for a specific file"""
    import_script = os.path.join(os.path.dirname(__file__), '..', 'database', 'import_data.py')
    
    try:
        # Use PowerShell syntax for running the import
        cmd = f'python "{import_script}" --file "{file_path}"'
        print(f"Running: {cmd}")
        
        result = subprocess.run(
            ['powershell', '-Command', cmd],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), '..')
        )
        
        if result.returncode == 0:
            print("✅ Import successful")
            return True, result.stdout
        else:
            print(f"❌ Import failed with return code {result.returncode}")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False, result.stderr
            
    except Exception as e:
        print(f"❌ Error running import: {e}")
        return False, str(e)

def bulk_reimport():
    """Re-import all available output files"""
    
    print("=== Bulk Re-import Process ===\n")
    
    # Find all output files
    output_files = find_all_output_files()
    
    if not output_files:
        print("No output files found for re-import")
        return
    
    print(f"Found {len(output_files)} output files:")
    for i, file_path in enumerate(output_files, 1):
        filename = os.path.basename(file_path)
        print(f"  {i:2d}. {filename}")
    
    print()
    
    # Ask for confirmation
    confirm = input(f"Proceed with importing all {len(output_files)} files? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Re-import cancelled.")
        return
    
    print("\n=== Starting Re-import Process ===\n")
    
    successful_imports = []
    failed_imports = []
    
    for i, file_path in enumerate(output_files, 1):
        filename = os.path.basename(file_path)
        print(f"[{i}/{len(output_files)}] Importing {filename}...")
        
        success, output = run_import(file_path)
        
        if success:
            successful_imports.append(filename)
        else:
            failed_imports.append((filename, output))
        
        print()
    
    # Summary
    print("=== Re-import Summary ===")
    print(f"✅ Successful imports: {len(successful_imports)}")
    for filename in successful_imports:
        print(f"    {filename}")
    
    if failed_imports:
        print(f"\n❌ Failed imports: {len(failed_imports)}")
        for filename, error in failed_imports:
            print(f"    {filename}: {error[:100]}...")
    
    print(f"\nTotal: {len(successful_imports)}/{len(output_files)} imports successful")

if __name__ == "__main__":
    bulk_reimport()
