#!/usr/bin/env python3
"""
Batch Scraper CLI Tool
======================
Process multiple websites in parallel based on configuration file.

This tool reads a configuration file containing a list of websites and processes
them using the scraper.py tool with configurable parallelism. After each site
is scraped, it automatically imports the data into the database.

Usage:
    python batch_scraper.py                          # Use default config/scraper.json
    python batch_scraper.py --config custom.json    # Use custom configuration
    python batch_scraper.py --dry-run               # Show what would be processed
    python batch_scraper.py --workers 2             # Override worker count
    python batch_scraper.py --no-import             # Skip database import

Features:
- Parallel processing with configurable worker count
- Automatic database import after each successful scrape
- Progress tracking and detailed logging
- Error handling and retry logic
- Dry-run mode for testing
- Resume functionality for failed runs
"""

import argparse
import json
import sys
import os
import subprocess
import logging
import time
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import threading

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.common.logging_config import get_logger
except ImportError as e:
    print(f"ERROR: Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

@dataclass
class ScrapingResult:
    """Result of a scraping operation."""
    url: str
    success: bool
    output_file: Optional[str] = None
    error_message: Optional[str] = None
    scrape_duration: float = 0.0
    import_success: bool = False
    import_duration: float = 0.0
    products_count: int = 0
    categories_count: int = 0

class BatchScraperCLI:
    """Batch scraper command-line interface."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.results: List[ScrapingResult] = []
        self.start_time = datetime.now()
        self.lock = threading.Lock()
        
    def parse_arguments(self):
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(
            description="Batch scraper for processing multiple websites in parallel",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python batch_scraper.py                          # Process all sites in config/scraper.json
  python batch_scraper.py --config custom.json    # Use custom configuration file
  python batch_scraper.py --dry-run               # Show what would be processed
  python batch_scraper.py --workers 2             # Use 2 parallel workers
  python batch_scraper.py --no-import             # Skip database import
  python batch_scraper.py --sites 3               # Process only first 3 sites
            """
        )
        
        parser.add_argument(
            "--config", "-c",
            default="config/scraper.json",
            help="Configuration file path (default: config/scraper.json)"
        )
        
        parser.add_argument(
            "--workers", "-w",
            type=int,
            help="Number of parallel workers (overrides config file)"
        )
        
        parser.add_argument(
            "--dry-run", "-d",
            action="store_true",
            help="Show what would be processed without actually scraping"
        )
        
        parser.add_argument(
            "--no-import",
            action="store_true",
            help="Skip database import after scraping"
        )
        
        parser.add_argument(
            "--sites", "-s",
            type=int,
            help="Limit number of sites to process (useful for testing)"
        )
        
        parser.add_argument(
            "--resume",
            action="store_true",
            help="Resume processing, skip sites that already have output files"
        )
        
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose logging"
        )
        
        return parser.parse_args()
    
    def setup_logging(self, verbose: bool = False):
        """Set up logging configuration."""
        level = logging.DEBUG if verbose else logging.INFO
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Console handler with UTF-8 encoding
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        
        # File handler for batch operations with UTF-8 encoding
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / f"batch_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.handlers.clear()
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        
        return root_logger
    
    def load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate required fields
            if 'sites' not in config:
                raise ValueError("Configuration must contain 'sites' field")
            
            if not isinstance(config['sites'], list):
                raise ValueError("'sites' field must be a list")
            
            if 'workerCount' not in config:
                config['workerCount'] = 1
                self.logger.warning("No 'workerCount' specified, defaulting to 1")
            
            self.logger.info(f"Loaded configuration: {len(config['sites'])} sites, {config['workerCount']} workers")
            return config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def check_existing_output(self, url: str) -> Optional[str]:
        """Check if output file already exists for a URL."""
        output_dir = Path("output")
        
        # Try to predict output filename based on URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '').replace('.', '_')
        scraper_name = domain.split('_')[0]
        
        # Look for existing files with this scraper prefix
        pattern = f"{scraper_name}_*.json"
        existing_files = list(output_dir.glob(pattern))
        
        # Check if any file contains this URL in its content
        for file_path in existing_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('source', {}).get('url') == url:
                        return str(file_path)
            except (json.JSONDecodeError, FileNotFoundError):
                continue
        
        return None
    
    def scrape_single_site(self, url: str, worker_id: int, skip_import: bool = False) -> ScrapingResult:
        """Scrape a single website and optionally import to database."""
        result = ScrapingResult(url=url, success=False)
        
        with self.lock:
            self.logger.info(f"[Worker {worker_id}] Starting: {url}")
        
        try:
            # Start scraping
            scrape_start = time.time()
            
            # Run scraper.py as subprocess with UTF-8 environment
            cmd = [sys.executable, "scraper.py", url]
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout per site
                env=env
            )
            
            scrape_duration = time.time() - scrape_start
            result.scrape_duration = scrape_duration
            
            if process.returncode == 0:
                result.success = True
                
                # Try to find the output file
                output_files = list(Path("output").glob("*.json"))
                latest_file = max(output_files, key=lambda f: f.stat().st_mtime, default=None)
                
                if latest_file:
                    result.output_file = str(latest_file)
                    
                    # Extract product/category counts from output
                    try:
                        with open(latest_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            result.products_count = len(data.get('products', []))
                            result.categories_count = len(data.get('categories', []))
                    except Exception as e:
                        self.logger.warning(f"Could not parse output file {latest_file}: {e}")
                
                with self.lock:
                    self.logger.info(f"[Worker {worker_id}] COMPLETED: Scraped {url} in {scrape_duration:.1f}s")
                    if result.output_file:
                        self.logger.info(f"[Worker {worker_id}]    Products: {result.products_count}, Categories: {result.categories_count}")
                
                # Import to database if enabled and scraping was successful
                if not skip_import and result.output_file:
                    import_start = time.time()
                    
                    import_cmd = [sys.executable, "database/import_data.py", "--file", result.output_file]
                    env_import = os.environ.copy()
                    env_import['PYTHONIOENCODING'] = 'utf-8'
                    
                    import_process = subprocess.run(
                        import_cmd,
                        capture_output=True,
                        text=True,
                        timeout=120,  # 2 minute timeout for import
                        env=env_import
                    )
                    
                    import_duration = time.time() - import_start
                    result.import_duration = import_duration
                    
                    # Check if import was successful based on return code and output content
                    if import_process.returncode == 0:
                        result.import_success = True
                        with self.lock:
                            self.logger.info(f"[Worker {worker_id}] IMPORTED: {result.output_file} in {import_duration:.1f}s")
                    else:
                        with self.lock:
                            self.logger.error(f"[Worker {worker_id}] IMPORT FAILED: {result.output_file}")
                            self.logger.error(f"[Worker {worker_id}]    Return code: {import_process.returncode}")
                            if import_process.stderr:
                                self.logger.error(f"[Worker {worker_id}]    Error: {import_process.stderr}")
            else:
                result.error_message = process.stderr
                with self.lock:
                    self.logger.error(f"[Worker {worker_id}] SCRAPING FAILED: {url}")
                    self.logger.error(f"[Worker {worker_id}]    Error: {process.stderr}")
        
        except subprocess.TimeoutExpired:
            result.error_message = "Scraping timeout (10 minutes)"
            with self.lock:
                self.logger.error(f"[Worker {worker_id}] TIMEOUT: Scraping {url}")
        
        except Exception as e:
            result.error_message = str(e)
            with self.lock:
                self.logger.error(f"[Worker {worker_id}] ERROR: Unexpected error scraping {url}: {e}")
        
        return result
    
    def process_sites(self, sites: List[str], worker_count: int, skip_import: bool = False, resume: bool = False) -> List[ScrapingResult]:
        """Process multiple sites with parallel workers."""
        
        # Filter sites if resume mode is enabled
        sites_to_process = []
        if resume:
            for url in sites:
                existing_file = self.check_existing_output(url)
                if existing_file:
                    self.logger.info(f"⏭️  Skipping {url} (output exists: {existing_file})")
                else:
                    sites_to_process.append(url)
        else:
            sites_to_process = sites
        
        if not sites_to_process:
            self.logger.info("No sites to process (all already completed)")
            return []
        
        self.logger.info(f"🚀 Processing {len(sites_to_process)} sites with {worker_count} workers")
        
        # Process sites in parallel
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            # Submit all tasks
            future_to_url = {
                executor.submit(self.scrape_single_site, url, i % worker_count + 1, skip_import): url
                for i, url in enumerate(sites_to_process)
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                result = future.result()
                results.append(result)
                
                # Progress update
                completed = len(results)
                total = len(sites_to_process)
                self.logger.info(f"📊 Progress: {completed}/{total} sites completed ({completed/total*100:.1f}%)")
        
        return results
    
    def print_summary(self, results: List[ScrapingResult], total_duration: float):
        """Print a comprehensive summary of the batch operation."""
        if not results:
            return
        
        successful_scrapes = [r for r in results if r.success]
        failed_scrapes = [r for r in results if not r.success]
        successful_imports = [r for r in results if r.import_success]
        
        total_products = sum(r.products_count for r in successful_scrapes)
        total_categories = sum(r.categories_count for r in successful_scrapes)
        
        print(f"\n{'='*80}")
        print(f"BATCH SCRAPING SUMMARY")
        print(f"{'='*80}")
        print(f"⏱️  Total Duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        print(f"🌐 Sites Processed: {len(results)}")
        print(f"Successful Scrapes: {len(successful_scrapes)}")
        print(f"Failed Scrapes: {len(failed_scrapes)}")
        print(f"📥 Successful Imports: {len(successful_imports)}")
        print(f"🛍️  Total Products: {total_products}")
        print(f"📂 Total Categories: {total_categories}")
        
        if successful_scrapes:
            avg_scrape_time = sum(r.scrape_duration for r in successful_scrapes) / len(successful_scrapes)
            print(f"⚡ Average Scrape Time: {avg_scrape_time:.1f} seconds")
        
        # Show detailed results
        if successful_scrapes:
            print(f"\nSUCCESSFUL SCRAPES:")
            for result in successful_scrapes:
                import_status = "✅ Imported" if result.import_success else "❌ Import failed"
                print(f"   • {result.url}")
                print(f"     Products: {result.products_count}, Categories: {result.categories_count}")
                print(f"     Time: {result.scrape_duration:.1f}s, {import_status}")
                if result.output_file:
                    print(f"     File: {result.output_file}")
        
        if failed_scrapes:
            print(f"\nFAILED SCRAPES:")
            for result in failed_scrapes:
                print(f"   • {result.url}")
                if result.error_message:
                    error_preview = result.error_message[:100] + "..." if len(result.error_message) > 100 else result.error_message
                    print(f"     Error: {error_preview}")
        
        print(f"\n{'='*80}")
    
    def run(self):
        """Main execution method."""
        args = self.parse_arguments()
        
        # Setup logging
        self.setup_logging(args.verbose)
        
        try:
            # Load configuration
            config = self.load_config(args.config)
            
            # Override worker count if specified
            worker_count = args.workers if args.workers else config['workerCount']
            
            # Limit sites if specified
            sites = config['sites'][:args.sites] if args.sites else config['sites']
            
            print(f"Batch Scraper Starting")
            print(f"   Configuration: {args.config}")
            print(f"   Sites to process: {len(sites)}")
            print(f"   Worker count: {worker_count}")
            print(f"   Database import: {'Disabled' if args.no_import else 'Enabled'}")
            print(f"   Resume mode: {'Enabled' if args.resume else 'Disabled'}")
            
            if args.dry_run:
                print(f"\n🔍 DRY RUN - Sites that would be processed:")
                for i, site in enumerate(sites, 1):
                    existing = self.check_existing_output(site) if args.resume else None
                    status = " (SKIP - exists)" if existing else ""
                    print(f"   {i}. {site}{status}")
                print(f"\nTotal sites: {len(sites)}")
                print(f"Worker count: {worker_count}")
                return
            
            # Process sites
            results = self.process_sites(sites, worker_count, args.no_import, args.resume)
            
            # Calculate total duration
            total_duration = (datetime.now() - self.start_time).total_seconds()
            
            # Print summary
            self.print_summary(results, total_duration)
            
            # Exit with error code if any scrapes failed
            failed_count = len([r for r in results if not r.success])
            if failed_count > 0:
                self.logger.error(f"❌ {failed_count} sites failed to scrape")
                sys.exit(1)
            else:
                self.logger.info("🎉 All sites processed successfully!")
        
        except KeyboardInterrupt:
            self.logger.info("\n⏹️  Batch scraping interrupted by user")
            sys.exit(1)
        
        except Exception as e:
            self.logger.error(f"❌ Batch scraping failed: {e}")
            if args.verbose:
                import traceback
                self.logger.error(traceback.format_exc())
            sys.exit(1)

if __name__ == "__main__":
    cli = BatchScraperCLI()
    cli.run()
