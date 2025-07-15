"""
Demo script to test the configuration loading system.

This script demonstrates how to use the ScraperFactory to load
and work with website configurations.
"""
import os
import sys

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from common import ScraperFactory, setup_logging, get_logger


def main():
    """Main demonstration function."""
    # Set up logging
    setup_logging(log_level="INFO")
    logger = get_logger(__name__)
    
    logger.info("Starting configuration demo")
    
    # Initialize the factory
    factory = ScraperFactory()
    
    # Show available configurations
    domains = factory.list_available_domains()
    logger.info(f"Available configurations: {domains}")
    
    # Get configuration summary
    summary = factory.get_config_summary()
    print("\n=== Configuration Summary ===")
    for domain, info in summary.items():
        print(f"\nDomain: {domain}")
        print(f"  Base URL: {info['base_url']}")
        print(f"  Scraping Method: {info['scraping_method']}")
        print(f"  Requires JavaScript: {info['requires_javascript']}")
        print(f"  Anti-bot Protection: {info['anti_bot_protection']}")
        print(f"  URL Pattern: {info['url_pattern']}")
        print(f"  Has Testing URLs: {info['has_testing_urls']}")
    
    # Test URL matching
    test_urls = [
        "https://www.foody.com.cy/delivery/menu/costa-coffee",
        "https://foody.com/some-restaurant",
        "https://www.unknown-site.com/menu"
    ]
    
    print("\n=== URL Matching Tests ===")
    for url in test_urls:
        config = factory.get_config_for_url(url)
        if config:
            print(f"✓ {url} -> {config.domain} ({config.scraping_method})")
        else:
            print(f"✗ {url} -> No configuration found")
    
    # Test specific domain lookup
    print("\n=== Domain Lookup Tests ===")
    test_domains = ["foody.com.cy", "foody.com", "unknown.com"]
    for domain in test_domains:
        config = factory.get_config_by_domain(domain)
        if config:
            print(f"✓ {domain} -> Found configuration")
            print(f"  Selectors: title='{config.title_selector}', price='{config.price_selector}'")
        else:
            print(f"✗ {domain} -> No configuration found")


if __name__ == "__main__":
    main()
