#!/usr/bin/env python3
"""
Simple CLI scraper script for web scraping with automatic config selection.

Usage:
    python scraper.py <url>
    python scraper.py https://www.foody.com.cy/delivery/menu/costa-coffee

Features:
- Automatic scraper configuration selection based on URL
- Progress logging and status updates
- JSON output saved to output/ directory with format: scraper_restaurant.json
- Error handling for invalid URLs and unsupported sites
"""

import argparse
import sys
import os
import json
import logging
import re
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.common.factory import ScraperFactory
    from src.scrapers.foody_scraper import FoodyScraper
    from src.scrapers.wolt_scraper import WoltScraper
    from src.common.logging_config import get_logger
except ImportError as e:
    print(f"ERROR: Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

class ScraperCLI:
    """Command-line interface for the web scraper."""
    
    def __init__(self):
        self.factory = ScraperFactory()
        self.logger = get_logger(__name__)
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    def parse_arguments(self):
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(
            description="Web scraper with automatic configuration selection",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python scraper.py https://www.foody.com.cy/delivery/menu/costa-coffee
  python scraper.py https://www.foody.com.cy/delivery/menu/mcdonalds
  
Output:
  JSON files are saved to the output/ directory with format: scraper_restaurant.json
            """
        )
        
        parser.add_argument(
            'url',
            nargs='?',  # Make URL optional
            help='URL to scrape (e.g., https://www.foody.com.cy/delivery/menu/costa-coffee)'
        )
        
        parser.add_argument(
            '-o', '--output',
            help='Output file path (default: auto-generated in output/ directory)',
            default=None
        )
        
        parser.add_argument(
            '-v', '--verbose',
            action='store_true',
            help='Enable verbose logging output'
        )
        
        parser.add_argument(
            '--list-configs',
            action='store_true',
            help='List available scraper configurations'
        )
        
        return parser.parse_args()
    
    def setup_logging(self, verbose=False):
        """Setup logging configuration."""
        level = logging.DEBUG if verbose else logging.INFO
        
        # Configure console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.handlers.clear()
        root_logger.addHandler(console_handler)
        
        return root_logger
    
    def validate_url(self, url):
        """Validate and normalize the input URL."""
        try:
            parsed = urlparse(url)
            
            if not parsed.scheme:
                # Add https if no scheme provided
                url = f"https://{url}"
                parsed = urlparse(url)
            
            if not parsed.netloc:
                raise ValueError("Invalid URL format")
            
            if parsed.scheme not in ['http', 'https']:
                raise ValueError("URL must use HTTP or HTTPS protocol")
            
            return url
            
        except Exception as e:
            raise ValueError(f"Invalid URL '{url}': {e}")
    
    def list_available_configs(self):
        """List all available scraper configurations."""
        print("📋 Available Scraper Configurations:")
        print()
        
        try:
            domains = self.factory.list_available_domains()
            
            if not domains:
                print("No scraper configurations found.")
                return
            
            for i, domain in enumerate(domains, 1):
                print(f"{i}. {domain}")
            
            print(f"\nTotal configurations: {len(domains)}")
            
        except Exception as e:
            print(f"❌ Error listing configurations: {e}")
    
    def select_scraper_config(self, url):
        """Select the appropriate scraper configuration for the URL."""
        print(f"🔍 Finding scraper configuration for: {url}")
        
        try:
            config = self.factory.get_config_for_url(url)
            
            if not config:
                print(f"❌ No scraper configuration found for URL: {url}")
                print(f"\nSupported domains:")
                domains = self.factory.list_available_domains()
                for domain in domains:
                    print(f"  • {domain}")
                return None
            
            print(f"✅ Found configuration for: {config.domain}")
            print(f"   Scraping method: {config.scraping_method}")
            print(f"   Requires JavaScript: {config.requires_javascript}")
            
            return config
            
        except Exception as e:
            print(f"❌ Error selecting scraper config: {e}")
            return None
    
    def create_scraper(self, config, url):
        """Create the appropriate scraper instance."""
        try:
            # Create scraper based on domain - handle multiple domain variations
            domain = config.domain.lower()
            
            if "foody" in domain:  # Handles foody.com.cy, foody.com, etc.
                return FoodyScraper(config, url)
            elif "wolt" in domain:  # Handles wolt.com, wolt.com.cy, etc.
                return WoltScraper(config, url)
            else:
                raise ValueError(f"Scraper not implemented for domain: {config.domain}")
                
        except Exception as e:
            print(f"❌ Error creating scraper: {e}")
            return None
    
    def generate_output_path(self, url, output_path=None, results=None):
        """Generate output filename based on scraper name and restaurant name."""
        if output_path:
            return Path(output_path)
        
        # Parse URL to get domain for scraper name
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '').replace('.', '_')
        scraper_name = domain.split('_')[0]  # e.g., 'foody' from 'foody_com_cy'
        
        # Try to get restaurant name from results
        restaurant_name = "unknown"
        if results and 'restaurant' in results and 'name' in results['restaurant']:
            raw_name = results['restaurant']['name']
            if raw_name:
                # Sanitize restaurant name for filename
                # Remove common suffixes and clean the name
                clean_name = raw_name.lower()
                clean_name = re.sub(r'\s+(online\s+delivery|order\s+from\s+foody|delivery)\s*$', '', clean_name)
                clean_name = re.sub(r'[^\w\s-]', '', clean_name)  # Remove special chars
                clean_name = re.sub(r'\s+', '-', clean_name)  # Replace spaces with hyphens
                clean_name = re.sub(r'-+', '-', clean_name)  # Collapse multiple hyphens
                clean_name = clean_name.strip('-')  # Remove leading/trailing hyphens
                
                if clean_name:
                    restaurant_name = clean_name
        
        # Generate filename: scraper_restaurant.json
        filename = f"{scraper_name}_{restaurant_name}.json"
        return self.output_dir / filename
    
    def save_results(self, results, output_path):
        """Save scraping results to JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            file_size = os.path.getsize(output_path)
            print(f"💾 Results saved to: {output_path}")
            print(f"   File size: {file_size:,} bytes")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return False
    
    def print_summary(self, results):
        """Print a summary of scraping results."""
        print(f"\n📊 Scraping Summary:")
        print(f"   Restaurant: {results.get('restaurant', {}).get('name', 'Unknown')}")
        print(f"   Categories: {len(results.get('categories', []))}")
        print(f"   Products: {len(results.get('products', []))}")
        print(f"   Errors: {len(results.get('errors', []))}")
        
        # Show processing time
        metadata = results.get('metadata', {})
        if 'processing_duration_seconds' in metadata:
            duration = metadata['processing_duration_seconds']
            print(f"   Processing time: {duration:.3f}s")
        
        # Show errors if any
        errors = results.get('errors', [])
        if errors:
            print(f"\n⚠️  Errors encountered:")
            for error in errors[:3]:  # Show first 3 errors
                print(f"   • {error.get('type', 'Unknown')}: {error.get('message', 'No message')[:80]}...")
            
            if len(errors) > 3:
                print(f"   ... and {len(errors) - 3} more errors")
    
    def run_scraper(self, url, output_path=None, verbose=False):
        """Main scraper execution logic."""
        print(f"🚀 Starting web scraper...")
        print(f"   Target URL: {url}")
        print()
        
        # Setup logging
        logger = self.setup_logging(verbose)
        
        try:
            # 1. Validate URL
            url = self.validate_url(url)
            print(f"✅ URL validated: {url}")
            
            # 2. Select scraper configuration
            config = self.select_scraper_config(url)
            if not config:
                return False
            
            # 3. Create scraper instance
            print(f"🔧 Creating scraper...")
            scraper = self.create_scraper(config, url)
            if not scraper:
                return False
            
            print(f"✅ Scraper created successfully")
            
            # 4. Run scraping
            print(f"\n🔄 Starting scraping process...")
            print(f"   This may take a few seconds...")
            
            results = scraper.scrape()
            
            if not results:
                print(f"❌ Scraping failed - no results returned")
                return False
            
            print(f"✅ Scraping completed successfully")
            
            # 5. Generate output filename with restaurant name
            output_file = self.generate_output_path(url, output_path, results)
            print(f"\n💾 Saving results...")
            
            if not self.save_results(results, output_file):
                return False
            
            # 6. Print summary
            self.print_summary(results)
            
            print(f"\n🎉 Scraping completed successfully!")
            return True
            
        except KeyboardInterrupt:
            print(f"\n⚠️  Scraping interrupted by user")
            return False
            
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            return False
    
    def main(self):
        """Main CLI entry point."""
        try:
            args = self.parse_arguments()
            
            # Handle list configs command
            if args.list_configs:
                self.list_available_configs()
                return True
            
            # Validate URL argument
            if not args.url:
                print("❌ URL argument is required")
                print("\nUsage:")
                print("  python scraper.py <url>")
                print("  python scraper.py --list-configs")
                print("\nExamples:")
                print("  python scraper.py https://www.foody.com.cy/delivery/menu/costa-coffee")
                return False
            
            # Run the scraper
            return self.run_scraper(args.url, args.output, args.verbose)
            
        except Exception as e:
            print(f"❌ CLI error: {e}")
            return False


if __name__ == "__main__":
    cli = ScraperCLI()
    success = cli.main()
    sys.exit(0 if success else 1)
    """Command-line interface for the web scraper."""
    
    def __init__(self):
        self.factory = ScraperFactory()
        self.logger = get_logger(__name__)
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    def parse_arguments(self):
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(
            description="Web scraper with automatic configuration selection",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python scraper.py https://www.foody.com.cy/delivery/menu/costa-coffee
  python scraper.py https://www.foody.com.cy/delivery/menu/mcdonalds
  
Output:
  JSON files are saved to the output/ directory with timestamps.
            """
        )
        
        parser.add_argument(
            'url',
            nargs='?',  # Make URL optional
            help='URL to scrape (e.g., https://www.foody.com.cy/delivery/menu/costa-coffee)'
        )
        
        parser.add_argument(
            '-o', '--output',
            help='Output file path (default: auto-generated in output/ directory)',
            default=None
        )
        
        parser.add_argument(
            '-v', '--verbose',
            action='store_true',
            help='Enable verbose logging output'
        )
        
        parser.add_argument(
            '--list-configs',
            action='store_true',
            help='List available scraper configurations'
        )
        
        return parser.parse_args()
    
    def setup_logging(self, verbose=False):
        """Setup logging configuration."""
        level = logging.DEBUG if verbose else logging.INFO
        
        # Configure console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.handlers.clear()
        root_logger.addHandler(console_handler)
        
        return root_logger
    
    def validate_url(self, url):
        """Validate and normalize the input URL."""
        try:
            parsed = urlparse(url)
            
            if not parsed.scheme:
                # Add https if no scheme provided
                url = f"https://{url}"
                parsed = urlparse(url)
            
            if not parsed.netloc:
                raise ValueError("Invalid URL format")
            
            if parsed.scheme not in ['http', 'https']:
                raise ValueError("URL must use HTTP or HTTPS protocol")
            
            return url
            
        except Exception as e:
            raise ValueError(f"Invalid URL '{url}': {e}")
    
    def list_available_configs(self):
        """List all available scraper configurations."""
        print("📋 Available Scraper Configurations:")
        print()
        
        try:
            domains = self.factory.list_available_domains()
            
            if not domains:
                print("No scraper configurations found.")
                return
            
            for i, domain in enumerate(domains, 1):
                print(f"{i}. {domain}")
            
            print(f"\nTotal configurations: {len(domains)}")
            
        except Exception as e:
            print(f"❌ Error listing configurations: {e}")
    
    def select_scraper_config(self, url):
        """Select the appropriate scraper configuration for the URL."""
        print(f"🔍 Finding scraper configuration for: {url}")
        
        try:
            config = self.factory.get_config_for_url(url)
            
            if not config:
                print(f"❌ No scraper configuration found for URL: {url}")
                print(f"\nSupported domains:")
                domains = self.factory.list_available_domains()
                for domain in domains:
                    print(f"  • {domain}")
                return None
            
            print(f"✅ Found configuration for: {config.domain}")
            print(f"   Scraping method: {config.scraping_method}")
            print(f"   Requires JavaScript: {config.requires_javascript}")
            
            return config
            
        except Exception as e:
            print(f"❌ Error selecting scraper config: {e}")
            return None
    
    def create_scraper(self, config, url):
        """Create the appropriate scraper instance."""
        try:
            # For now, we only have FoodyScraper implemented
            if config.domain == "foody.com.cy":
                return FoodyScraper(config, url)
            else:
                raise ValueError(f"Scraper not implemented for domain: {config.domain}")
                
        except Exception as e:
            print(f"❌ Error creating scraper: {e}")
            return None
    
    def generate_output_filename(self, url, output_path=None):
        """Generate output filename based on URL and timestamp."""
        if output_path:
            return Path(output_path)
        
        # Parse URL to create filename
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '').replace('.', '_')
        
        # Create timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Generate filename
        filename = f"{domain}_{timestamp}.json"
        return self.output_dir / filename
    
    def save_results(self, results, output_path):
        """Save scraping results to JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            file_size = os.path.getsize(output_path)
            print(f"💾 Results saved to: {output_path}")
            print(f"   File size: {file_size:,} bytes")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return False
    
    def print_summary(self, results):
        """Print a summary of scraping results."""
        print(f"\n📊 Scraping Summary:")
        print(f"   Restaurant: {results.get('restaurant', {}).get('name', 'Unknown')}")
        print(f"   Categories: {len(results.get('categories', []))}")
        print(f"   Products: {len(results.get('products', []))}")
        print(f"   Errors: {len(results.get('errors', []))}")
        
        # Show processing time
        metadata = results.get('metadata', {})
        if 'processing_duration_seconds' in metadata:
            duration = metadata['processing_duration_seconds']
            print(f"   Processing time: {duration:.3f}s")
        
        # Show errors if any
        errors = results.get('errors', [])
        if errors:
            print(f"\n⚠️  Errors encountered:")
            for error in errors[:3]:  # Show first 3 errors
                print(f"   • {error.get('type', 'Unknown')}: {error.get('message', 'No message')[:80]}...")
            
            if len(errors) > 3:
                print(f"   ... and {len(errors) - 3} more errors")
    
    def run_scraper(self, url, output_path=None, verbose=False):
        """Main scraper execution logic."""
        print(f"🚀 Starting web scraper...")
        print(f"   Target URL: {url}")
        print()
        
        # Setup logging
        logger = self.setup_logging(verbose)
        
        try:
            # 1. Validate URL
            url = self.validate_url(url)
            print(f"✅ URL validated: {url}")
            
            # 2. Select scraper configuration
            config = self.select_scraper_config(url)
            if not config:
                return False
            
            # 3. Create scraper instance
            print(f"🔧 Creating scraper...")
            scraper = self.create_scraper(config, url)
            if not scraper:
                return False
            
            print(f"✅ Scraper created successfully")
            
            # 4. Run scraping
            print(f"\n🔄 Starting scraping process...")
            print(f"   This may take a few seconds...")
            
            results = scraper.scrape()
            
            if not results:
                print(f"❌ Scraping failed - no results returned")
                return False
            
            print(f"✅ Scraping completed successfully")
            
            # 5. Save results
            output_file = self.generate_output_filename(url, output_path)
            print(f"\n💾 Saving results...")
            
            if not self.save_results(results, output_file):
                return False
            
            # 6. Print summary
            self.print_summary(results)
            
            print(f"\n🎉 Scraping completed successfully!")
            return True
            
        except KeyboardInterrupt:
            print(f"\n⚠️  Scraping interrupted by user")
            return False
            
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            return False
    
    def main(self):
        """Main CLI entry point."""
        try:
            args = self.parse_arguments()
            
            # Handle list configs command
            if args.list_configs:
                self.list_available_configs()
                return True
            
            # Validate URL argument
            if not args.url:
                print("❌ URL argument is required")
                print("Use --help for usage information")
                return False
            
            # Run the scraper
            success = self.run_scraper(
                url=args.url,
                output_path=args.output,
                verbose=args.verbose
            )
            
            return success
            
        except Exception as e:
            print(f"❌ CLI error: {e}")
            return False


def main():
    """Entry point for the CLI script."""
    cli = ScraperCLI()
    success = cli.main()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
