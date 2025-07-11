"""
Example script showing how to create and use scraper configurations.

This script demonstrates:
1. How to create a new configuration programmatically
2. How to save it to a markdown file
3. How to use the factory to load and work with configurations
"""
import os
import sys

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from common import ScraperConfig, ScraperFactory, setup_logging, get_logger


def create_new_config_example():
    """Create a new configuration example for a hypothetical website."""
    
    # Create a new configuration programmatically
    config = ScraperConfig(
        domain="wolt.com",
        base_url="https://wolt.com",
        item_selector=".restaurant-card",
        title_selector=".restaurant-name",
        price_selector=".delivery-fee",
        category_selector=".cuisine-tag",
        scraping_method="requests",
        requires_javascript=False,
        anti_bot_protection="none"
    )
    
    # Add some testing URLs
    config.testing_urls = [
        "https://wolt.com/en/discovery",
        "https://wolt.com/en/restaurants"
    ]
    
    # Add custom rules
    config.custom_rules = {
        "rating_selector": ".rating-value",
        "delivery_time_selector": ".delivery-time",
        "minimum_order_selector": ".minimum-order"
    }
    
    return config


def save_config_to_markdown(config: ScraperConfig, file_path: str):
    """Save a configuration to a markdown file in the simple format."""
    
    markdown_content = f"""# {config.domain.title()} Scraper Configuration

## Website Information
- **Domain**: {config.domain}
- **Base URL**: {config.base_url}
- **Scraping Method**: {config.scraping_method}
- **JavaScript Required**: {'Yes' if config.requires_javascript else 'No'}
- **Anti-bot Protection**: {config.anti_bot_protection}

## Selectors

### base_url
`{config.base_url}`

### item_selector
```css
{config.item_selector}
```

### title_selector
```css
{config.title_selector}
```

### price_selector
```css
{config.price_selector}
```

### category_selector
```css
{config.category_selector}
```

## Custom Rules
"""
    
    for key, value in config.custom_rules.items():
        markdown_content += f"- **{key.replace('_', ' ').title()}**: `{value}`\n"
    
    if config.testing_urls:
        markdown_content += "\n## Testing URLs\n"
        for i, url in enumerate(config.testing_urls, 1):
            markdown_content += f"- URL {i}: {url}\n"
    
    # Write to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)


def main():
    """Main example function."""
    setup_logging(log_level="INFO")
    logger = get_logger(__name__)
    
    print("=== Scraper Configuration Example ===\n")
    
    # 1. Create a new configuration
    print("1. Creating a new configuration for wolt.com...")
    wolt_config = create_new_config_example()
    print(f"   Created configuration: {wolt_config}")
    print(f"   Selectors: item='{wolt_config.item_selector}', title='{wolt_config.title_selector}'")
    print(f"   Custom rules: {list(wolt_config.custom_rules.keys())}")
    
    # 2. Save to markdown file
    output_file = "scrapers/wolt.md"
    print(f"\n2. Saving configuration to {output_file}...")
    save_config_to_markdown(wolt_config, output_file)
    print("   Configuration saved successfully!")
    
    # 3. Test loading the new configuration
    print(f"\n3. Testing loading of the new configuration...")
    try:
        loaded_config = ScraperConfig.from_markdown_file(output_file)
        print(f"   Loaded configuration: {loaded_config}")
        print(f"   Domain: {loaded_config.domain}")
        print(f"   Base URL: {loaded_config.base_url}")
        print(f"   Item selector: {loaded_config.item_selector}")
    except Exception as e:
        print(f"   Error loading configuration: {e}")
    
    # 4. Reload factory and test URL matching
    print(f"\n4. Testing with ScraperFactory...")
    factory = ScraperFactory()
    factory.reload_configs()  # Reload to pick up the new file
    
    test_urls = [
        "https://wolt.com/en/discovery",
        "https://www.foody.com.cy/delivery/menu/costa-coffee"
    ]
    
    for url in test_urls:
        config = factory.get_config_for_url(url)
        if config:
            print(f"   ✓ {url} -> {config.domain} ({config.scraping_method})")
        else:
            print(f"   ✗ {url} -> No configuration found")
    
    # 5. Show all available configurations
    print(f"\n5. All available configurations:")
    summary = factory.get_config_summary()
    for domain, info in summary.items():
        print(f"   - {domain}: {info['scraping_method']}, JS={info['requires_javascript']}")


if __name__ == "__main__":
    main()
