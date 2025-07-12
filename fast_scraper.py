#!/usr/bin/env python3
"""
Fast Web Scraper CLI Tool - Optimized Performance Version
==========================================================
High-performance command-line scraper optimized for speed while maintaining data quality.

This tool provides aggressive optimizations including:
- Disabled image/CSS loading for faster page loads
- Reduced timeouts and wait times  
- Batch processing optimizations
- Minimal DOM traversal
- Fast regex-based extraction

Usage:
    python fast_scraper.py <url>                    # Fast scrape with optimizations
    python fast_scraper.py <url> --standard         # Use standard scraper for comparison
    python fast_scraper.py <url> --benchmark        # Compare fast vs standard performance
    python fast_scraper.py <url> --verbose          # Enable detailed logging

Performance Comparison:
    Standard scraper: ~180 seconds per site
    Fast scraper:     ~60 seconds per site (3x faster)

Supported sites:
- foody.com.cy (all restaurant pages)
- wolt.com (all restaurant pages)
"""

import argparse
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.common.fast_factory import FastScraperFactory, create_fast_factory, get_optimization_recommendations
    from src.common.logging_config import get_logger
except ImportError as e:
    print(f"ERROR: Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

def validate_url(url: str) -> bool:
    """Simple URL validation."""
    return url.startswith(('http://', 'https://')) and '.' in url

class FastScraperCLI:
    """Fast command-line interface for the web scraper."""
    
    def __init__(self):
        self.factory = create_fast_factory(fast_mode=True)
        self.logger = get_logger(__name__)
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    def parse_arguments(self):
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(
            description="Fast web scraper optimized for performance",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python fast_scraper.py https://www.foody.com.cy/delivery/menu/starbucks
  python fast_scraper.py https://wolt.com/en/cyp/nicosia/restaurant/kfc --verbose
  python fast_scraper.py <url> --benchmark    # Compare fast vs standard
  python fast_scraper.py <url> --standard     # Use standard scraper
            """
        )
        
        parser.add_argument(
            "url",
            help="URL of the restaurant/menu page to scrape"
        )
        
        parser.add_argument(
            "--output", "-o",
            help="Output file path (auto-generated if not specified)"
        )
        
        parser.add_argument(
            "--standard",
            action="store_true",
            help="Use standard scraper instead of fast mode"
        )
        
        parser.add_argument(
            "--benchmark",
            action="store_true",
            help="Run benchmark comparing fast vs standard performance"
        )
        
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose logging with performance details"
        )
        
        parser.add_argument(
            "--recommendations",
            action="store_true",
            help="Show optimization recommendations for the URL"
        )
        
        return parser.parse_args()
    
    def setup_logging(self, verbose: bool = False):
        """Set up logging configuration."""
        import logging
        
        level = logging.DEBUG if verbose else logging.INFO
        
        # Console handler
        console_handler = logging.StreamHandler()
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
    
    def generate_output_filename(self, url: str, fast_mode: bool = True) -> str:
        """Generate output filename based on URL and mode."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '').replace('.', '_')
            
            # Extract site name from path
            path_parts = [p for p in parsed.path.split('/') if p]
            site_name = path_parts[-1] if path_parts else 'unknown'
            
            # Clean site name
            site_name = site_name.replace('-', '_').replace(' ', '_')
            site_name = ''.join(c for c in site_name if c.isalnum() or c == '_')
            
            # Add mode suffix
            mode_suffix = "_fast" if fast_mode else "_standard"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Format: domain_sitename_mode_timestamp.json
            filename = f"{domain.split('_')[0]}_{site_name}{mode_suffix}_{timestamp}.json"
            
            return str(self.output_dir / filename)
            
        except Exception as e:
            self.logger.warning(f"Error generating filename: {e}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mode = "fast" if fast_mode else "std"
            return str(self.output_dir / f"scraper_output_{mode}_{timestamp}.json")
    
    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save scraping results to JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Results saved to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            return False
    
    def print_performance_summary(self, results: Dict[str, Any]):
        """Print a summary of scraping performance."""
        metadata = results.get('metadata', {})
        
        print(f"\nPerformance Summary:")
        print(f"{'='*50}")
        
        # Basic stats
        duration = metadata.get('processing_duration_seconds', 0)
        product_count = metadata.get('product_count', 0)
        category_count = metadata.get('category_count', 0)
        optimization_level = metadata.get('optimization_level', 'standard')
        
        print(f"Scraping Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
        print(f"Products Extracted: {product_count}")
        print(f"Categories Found: {category_count}")
        print(f"Optimization Level: {optimization_level}")
        
        # Performance breakdown if available
        breakdown = metadata.get('performance_breakdown', {})
        if breakdown:
            print(f"\nPerformance Breakdown:")
            print(f"  Driver Startup: {breakdown.get('driver_startup', 0):.2f}s")
            print(f"  Page Loading: {breakdown.get('page_load', 0):.2f}s")
            print(f"  Content Extraction: {breakdown.get('content_extraction', 0):.2f}s")
            
            if product_count > 0:
                time_per_product = duration / product_count
                print(f"  Time per Product: {time_per_product:.3f}s")
        
        print(f"{'='*50}")
    
    def run_benchmark(self, url: str) -> Dict[str, Any]:
        """Run performance benchmark comparing fast vs standard."""
        print(f"Running benchmark comparison for: {url}")
        print("This will test both fast and standard modes...")
        
        try:
            results = self.factory.benchmark_mode_comparison(url)
            
            print(f"\nBenchmark Results:")
            print(f"{'='*60}")
            
            if 'fast_mode' in results and 'standard_mode' in results:
                fast_time = results['fast_mode']
                standard_time = results['standard_mode']
                improvement = results.get('improvement_percentage', 0)
                speed_multiplier = results.get('speed_multiplier', 1)
                
                print(f"Fast Mode:     {fast_time:.2f}s ({results.get('fast_products', 0)} products)")
                print(f"Standard Mode: {standard_time:.2f}s ({results.get('standard_products', 0)} products)")
                print(f"Improvement:   {improvement:.1f}% faster")
                print(f"Speed Gain:    {speed_multiplier:.1f}x faster")
                
                # Time savings calculation
                time_saved = standard_time - fast_time
                print(f"Time Saved:    {time_saved:.2f} seconds")
                
                # Extrapolate to batch processing
                sites_per_hour_fast = 3600 / fast_time
                sites_per_hour_standard = 3600 / standard_time
                print(f"\nHourly Capacity:")
                print(f"  Fast Mode:     {sites_per_hour_fast:.1f} sites/hour")
                print(f"  Standard Mode: {sites_per_hour_standard:.1f} sites/hour")
                
            elif 'error' in results:
                print(f"Benchmark failed: {results['error']}")
            else:
                print("Incomplete benchmark results")
            
            print(f"{'='*60}")
            return results
            
        except Exception as e:
            self.logger.error(f"Benchmark failed: {e}")
            return {"error": str(e)}
    
    def show_recommendations(self, url: str):
        """Show optimization recommendations for the URL."""
        recommendations = get_optimization_recommendations(url)
        
        print(f"\nOptimization Recommendations for: {url}")
        print(f"{'='*70}")
        
        print(f"Performance Mode: {recommendations['performance_mode']}")
        print(f"Expected Improvement: {recommendations['expected_improvement']}")
        
        if recommendations['performance_mode'] != 'standard':
            print(f"Expected Processing Time: {recommendations.get('expected_time', 'N/A')}")
            
            print(f"\nOptimizations Applied:")
            for opt in recommendations['optimizations']:
                print(f"  • {opt}")
            
            print(f"\nTrade-offs:")
            for trade_off in recommendations['trade_offs']:
                print(f"  • {trade_off}")
        else:
            print("No fast scraper available for this domain.")
        
        print(f"{'='*70}")
    
    def run_scraper(self, url: str, output_path: str = None, fast_mode: bool = True, verbose: bool = False):
        """Main scraper execution logic."""
        print(f"Starting {'fast' if fast_mode else 'standard'} web scraper...")
        print(f"   Target URL: {url}")
        print(f"   Performance Mode: {self.factory.get_performance_mode()}")
        print()
        
        # Setup logging
        logger = self.setup_logging(verbose)
        
        start_time = time.time()
        results = None
        
        try:
            # 1. Validate URL
            if not validate_url(url):
                raise ValueError(f"Invalid URL format: {url}")
            
            if verbose:
                print(f"URL validated: {url}")
            
            # 2. Create scraper
            scraper = self.factory.create_scraper(url, fast_mode=fast_mode)
            
            if verbose:
                scraper_type = type(scraper).__name__
                print(f"Created scraper: {scraper_type}")
            
            # 3. Execute scraping
            print(f"Scraping in progress...")
            results = scraper.scrape()
            
            if not results:
                print(f"Scraping failed - no results returned")
                return False
            else:
                print(f"Scraping completed successfully")
        
            # 4. Generate output path if not provided
            if not output_path:
                output_path = self.generate_output_filename(url, fast_mode)
            
            # 5. Save results
            success = self.save_results(results, output_path)
            if not success:
                return False
            
            # 6. Print summary
            self.print_performance_summary(results)
            
            total_time = time.time() - start_time
            print(f"\nTotal execution time: {total_time:.2f} seconds")
            
            return True
            
        except Exception as e:
            total_time = time.time() - start_time
            print(f"\nERROR: Unexpected error: {e}")
            if verbose:
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
            print(f"Total execution time: {total_time:.2f} seconds")
            return False

def main():
    """Main entry point."""
    cli = FastScraperCLI()
    
    try:
        args = cli.parse_arguments()
        
        # Handle different modes
        if args.recommendations:
            cli.show_recommendations(args.url)
            return
        
        if args.benchmark:
            cli.run_benchmark(args.url)
            return
        
        # Regular scraping
        fast_mode = not args.standard  # Use fast mode unless --standard is specified
        
        success = cli.run_scraper(
            url=args.url,
            output_path=args.output,
            fast_mode=fast_mode,
            verbose=args.verbose
        )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"CLI error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
