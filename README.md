# Web Scraper Configuration System

This project provides a flexible configuration system for web scraping different websites with their specific requirements.

## Project Structure

```
scraper-copilot/
├── src/
│   ├── common/
│   │   ├── __init__.py
│   │   ├── config.py          # ScraperConfig class
│   │   ├── factory.py         # ScraperFactory class
│   │   └── logging_config.py  # Logging setup
│   └── scrapers/              # Future scraper implementations
├── scrapers/                  # Configuration files
│   ├── template.md           # Template for new configs
│   ├── foody.md              # Foody.com.cy configuration
│   └── foody_com.md          # Alternative foody config
├── tests/
│   └── test_config.py        # Unit tests
├── output/                   # Scraping output directory
├── requirements.txt          # Python dependencies
├── demo_config.py           # Demonstration script
└── .env.example             # Environment variables template
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the configuration demo:**
   ```bash
   python demo_config.py
   ```

3. **Run tests:**
   ```bash
   python -m pytest tests/
   ```

## Configuration System

### ScraperConfig Class

The `ScraperConfig` class handles loading and parsing website-specific configurations from markdown files. It supports two formats:

#### Simple Template Format
```markdown
### base_url
`https://example.com`

### item_selector
```css
.product-card
```

### title_selector
`h3.product-title`
```

#### Detailed Format
```markdown
# Website Scraper Configuration

## Scraping Strategy
- **Method**: Selenium (JavaScript heavy site)
- **JavaScript Required**: Yes
- **URL Pattern**: `^https://www\.example\.com/products/.*`

## Testing URLs
- Primary: https://www.example.com/products/test
```

### ScraperFactory Class

The `ScraperFactory` manages multiple configurations and selects the appropriate one based on URL matching:

```python
from src.common import ScraperFactory

# Initialize factory (automatically loads all configs)
factory = ScraperFactory()

# Get configuration for a specific URL
config = factory.get_config_for_url("https://www.foody.com.cy/delivery/menu/costa-coffee")

if config:
    print(f"Using config for {config.domain}")
    print(f"Scraping method: {config.scraping_method}")
    print(f"Title selector: {config.title_selector}")
```

## Adding New Website Configurations

1. Create a new `.md` file in the `scrapers/` directory
2. Name it after the domain (e.g., `newsite_com.md`)
3. Follow the template format or detailed format
4. The factory will automatically load it on next initialization

### Configuration Options

- `base_url`: Base URL of the website
- `item_selector`: CSS selector for individual items/products
- `title_selector`: CSS selector for item titles
- `price_selector`: CSS selector for prices
- `category_selector`: CSS selector for categories
- `restaurant_name_selector`: CSS selector for restaurant names
- `brand_name_selector`: CSS selector for brand names
- `url_pattern`: Regex pattern to match URLs
- `requires_javascript`: Whether the site needs JavaScript rendering
- `scraping_method`: 'requests' or 'selenium'
- `anti_bot_protection`: Description of anti-bot measures
- `testing_urls`: List of URLs for testing
- `custom_rules`: Dictionary for site-specific extraction rules

## Logging

The project includes structured logging:

```python
from src.common import setup_logging, get_logger

# Set up logging
setup_logging(log_level="INFO", log_file="output/scraper.log")

# Get a logger
logger = get_logger(__name__)
logger.info("Starting scraper")
```

## Environment Configuration

Copy `.env.example` to `.env` and adjust settings:

```bash
cp .env.example .env
```

Key environment variables:
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FILE`: Path to log file
- `OUTPUT_DIR`: Directory for scraping output
- `DEFAULT_TIMEOUT`: Request timeout in seconds
- `HEADLESS_MODE`: Run browser in headless mode (true/false)

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src

# Run specific test file
python -m pytest tests/test_config.py -v
```

## BaseScraper Class

The project now includes a complete `BaseScraper` abstract base class that provides:

### Features
- ✅ **Unified JSON Output Format** - Consistent structure across all scrapers
- ✅ **Configuration-Driven** - Uses ScraperConfig for website-specific settings  
- ✅ **Error Handling** - Comprehensive error tracking and logging
- ✅ **Timestamp Management** - Automatic tracking of scrape and processing times
- ✅ **Abstract Methods** - `extract_restaurant_info()`, `extract_categories()`, `extract_products()`
- ✅ **Data Validation** - Built-in validation and price range calculations

### JSON Output Structure
```json
{
  "metadata": { "scraper_version", "domain", "timestamps", "counts" },
  "source": { "url", "domain", "scraped_at" },
  "restaurant": { "name", "brand", "address", "rating", "delivery_info" },
  "categories": [{ "id", "name", "description", "product_count" }],
  "products": [{ "id", "name", "price", "category", "availability", "options" }],
  "summary": { "totals", "price_range", "statistics" },
  "errors": [{ "type", "message", "timestamp", "context" }]
}
```

### Usage Example
```python
from src.common import ScraperFactory
from src.scrapers import BaseScraper

# Load configuration
factory = ScraperFactory()
config = factory.get_config_for_url("https://restaurant.com/menu")

# Implement scraper
class RestaurantScraper(BaseScraper):
    def extract_restaurant_info(self): # Implementation
    def extract_categories(self): # Implementation  
    def extract_products(self): # Implementation

# Run scraper
scraper = RestaurantScraper(config, target_url)
result = scraper.scrape()
output_file = scraper.save_output()
```

### Testing the BaseScraper
```bash
# Run the demo
python demo_scraper.py

# Run unit tests
python tests/test_base_scraper.py
```

## FoodyScraper Implementation

✅ **Complete Foody.com.cy Scraper** (`src/scrapers/foody_scraper.py`)
   - Extends BaseScraper for foody.com.cy restaurant platform
   - Uses requests + BeautifulSoup for HTTP extraction
   - Multiple strategies for restaurant name extraction
   - Retry logic with exponential backoff for reliability
   - Rate limiting and respectful scraping practices

### Current Capabilities
- ✅ **Restaurant Name Extraction** - Successfully extracts from H1, titles, meta tags
- ✅ **URL Validation** - Validates foody.com.cy URLs with regex patterns
- ✅ **JSON Output** - Complete unified format with metadata and timestamps
- ✅ **Error Handling** - Comprehensive error tracking and graceful degradation
- ⚠️  **Limited Products/Categories** - Basic structure due to JavaScript requirements

### Live Test Results
```bash
# Run the demo
python demo_foody_scraper.py

# Example output
✅ Restaurant: "Costa Coffee Online Delivery | Order from Foody"  
✅ Processing time: 0.49 seconds
✅ Valid JSON output: 1,318 bytes
⚠️  Products/Categories: Limited (requires Selenium for full extraction)
```

### Usage Example  
```python
from src.scrapers import FoodyScraper

scraper = FoodyScraper(config, "https://www.foody.com.cy/delivery/menu/costa-coffee")
result = scraper.scrape()
restaurant_name = result['restaurant']['name']  # "Costa Coffee..."
```

## Next Steps

This configuration system is ready for:
1. Implementing actual scraper classes
2. Adding data extraction logic
3. Implementing output formatting
4. Adding more sophisticated error handling
5. Creating a CLI interface

The foundation is flexible and extensible for various scraping scenarios.
