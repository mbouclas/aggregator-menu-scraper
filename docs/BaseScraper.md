# BaseScraper Documentation

## Overview

The `BaseScraper` class provides a unified foundation for web scraping different websites with standardized JSON output format. It handles configuration management, error logging, timestamp tracking, and output formatting.

## Architecture

```
BaseScraper (Abstract Base Class)
├── Configuration Management
├── Logging & Error Handling  
├── Timestamp Tracking
├── JSON Output Formatting
└── Abstract Methods for Implementation
```

## Key Features

✅ **Unified JSON Output Format** - Consistent structure across all scrapers
✅ **Configuration-Driven** - Uses ScraperConfig for website-specific settings
✅ **Error Handling** - Comprehensive error tracking and logging
✅ **Timestamp Management** - Automatic tracking of scrape and processing times
✅ **Extensible Architecture** - Abstract methods for custom implementations
✅ **Data Validation** - Built-in validation and summaries

## Usage

### 1. Basic Implementation

```python
from src.common import ScraperConfig
from src.scrapers import BaseScraper

class MyScraper(BaseScraper):
    def extract_restaurant_info(self) -> Dict[str, Any]:
        # Implementation for extracting restaurant details
        return {
            "name": "Restaurant Name",
            "brand": "Brand",
            "address": "Address",
            "phone": "Phone",
            "rating": 4.5,
            "delivery_fee": 2.50,
            "minimum_order": 15.00,
            "delivery_time": "30-45 min",
            "cuisine_types": ["Italian", "Pizza"]
        }
    
    def extract_categories(self) -> List[Dict[str, Any]]:
        # Implementation for extracting categories
        return [
            {
                "id": "cat_1",
                "name": "Category Name",
                "description": "Category Description",
                "product_count": 10
            }
        ]
    
    def extract_products(self) -> List[Dict[str, Any]]:
        # Implementation for extracting products
        return [
            {
                "id": "prod_1",
                "name": "Product Name",
                "description": "Product Description",
                "price": 12.50,
                "original_price": 15.00,
                "currency": "EUR",
                "discount_percentage": 16.67,
                "category": "Category Name",
                "image_url": "https://example.com/image.jpg",
                "availability": True,
                "options": [
                    {"name": "Size", "choices": ["Small", "Large"]}
                ]
            }
        ]
```

### 2. Using the Scraper

```python
# Load configuration
from src.common import ScraperFactory

factory = ScraperFactory()
config = factory.get_config_for_url("https://example.com/menu")

# Create and run scraper
scraper = MyScraper(config, "https://example.com/menu")
result = scraper.scrape()

# Save output
output_file = scraper.save_output()
```

## JSON Output Structure

The scraper produces a comprehensive JSON structure:

```json
{
  "metadata": {
    "scraper_version": "1.0.0",
    "domain": "example.com",
    "scraping_method": "selenium",
    "requires_javascript": true,
    "scraped_at": "2025-07-11T20:47:04.383786+00:00",
    "processed_at": "2025-07-11T20:47:04.383786+00:00",
    "processing_duration_seconds": 0.125,
    "error_count": 0,
    "product_count": 25,
    "category_count": 5
  },
  "source": {
    "url": "https://example.com/menu",
    "domain": "example.com",
    "scraped_at": "2025-07-11T20:47:04.383786+00:00"
  },
  "restaurant": {
    "name": "Restaurant Name",
    "brand": "Brand Name",
    "address": "Full Address",
    "phone": "+1234567890",
    "rating": 4.5,
    "delivery_fee": 2.50,
    "minimum_order": 15.00,
    "delivery_time": "30-45 min",
    "cuisine_types": ["Italian", "Pizza"]
  },
  "categories": [
    {
      "id": "unique_category_id",
      "name": "Category Name",
      "description": "Category Description",
      "product_count": 10
    }
  ],
  "products": [
    {
      "id": "unique_product_id",
      "name": "Product Name",
      "description": "Product Description",
      "price": 12.50,
      "original_price": 15.00,
      "currency": "EUR",
      "discount_percentage": 16.67,
      "category": "Category Name",
      "image_url": "https://example.com/image.jpg",
      "availability": true,
      "options": [
        {
          "name": "Size",
          "choices": ["Small", "Medium", "Large"]
        }
      ]
    }
  ],
  "summary": {
    "total_products": 25,
    "total_categories": 5,
    "price_range": {
      "min": 5.00,
      "max": 25.00,
      "average": 12.50,
      "currency": "EUR"
    },
    "available_products": 23,
    "products_with_discounts": 8
  },
  "errors": [
    {
      "type": "extraction_failed",
      "message": "Could not extract price for product X",
      "timestamp": "2025-07-11T20:47:04.383786+00:00",
      "context": {"product_id": "prod_123"}
    }
  ]
}
```

## Abstract Methods

All scrapers must implement these three methods:

### `extract_restaurant_info() -> Dict[str, Any]`

Extract basic restaurant/establishment information:

- **name**: Restaurant name
- **brand**: Brand name (can be same as name)
- **address**: Full address
- **phone**: Phone number
- **rating**: Rating (0.0-5.0)
- **delivery_fee**: Delivery fee amount
- **minimum_order**: Minimum order amount
- **delivery_time**: Estimated delivery time
- **cuisine_types**: List of cuisine types

### `extract_categories() -> List[Dict[str, Any]]`

Extract product categories with:

- **id**: Unique category identifier
- **name**: Category name
- **description**: Category description
- **product_count**: Number of products in category

### `extract_products() -> List[Dict[str, Any]]`

Extract individual products with:

- **id**: Unique product identifier
- **name**: Product name
- **description**: Product description
- **price**: Current price
- **original_price**: Original price (before discounts)
- **currency**: Currency code (e.g., "EUR", "USD")
- **discount_percentage**: Discount percentage
- **category**: Category name
- **image_url**: Product image URL
- **availability**: Whether product is available
- **options**: List of customization options

## Error Handling

The base scraper provides comprehensive error handling:

### Adding Errors

```python
self._add_error(
    error_type="extraction_failed",
    message="Could not extract price",
    context={"product_id": "prod_123", "selector": ".price"}
)
```

### Error Types

- `extraction_failed`: Failed to extract specific data
- `parsing_error`: Failed to parse extracted data
- `selector_not_found`: CSS selector not found
- `network_error`: Network/request failed
- `timeout_error`: Request timed out
- `validation_error`: Data validation failed

## Built-in Methods

### Data Access
- `get_config()`: Get scraper configuration
- `get_target_url()`: Get target URL
- `get_errors()`: Get list of errors
- `has_errors()`: Check if errors occurred
- `get_summary()`: Get scraping summary

### Output Management
- `scrape()`: Main scraping method
- `save_output(output_dir, filename)`: Save JSON to file
- `_build_output()`: Build final JSON structure

### Utilities
- `_generate_metadata()`: Generate metadata
- `_calculate_price_range()`: Calculate price statistics
- `_add_error()`: Add error to log

## Best Practices

### 1. Error Handling
```python
try:
    # Extraction logic
    price = self._extract_price(element)
except Exception as e:
    self.logger.error(f"Price extraction failed: {e}")
    self._add_error("price_extraction_failed", str(e), {"element": str(element)})
    price = 0.0  # Default value
```

### 2. Logging
```python
self.logger.info("Starting product extraction")
self.logger.debug(f"Found {len(products)} products")
self.logger.warning("Some products missing prices")
```

### 3. Data Validation
```python
# Validate required fields
if not product_name:
    self._add_error("missing_product_name", "Product name is empty")
    product_name = "Unknown Product"

# Validate data types
try:
    price = float(price_text.replace('€', '').strip())
except ValueError:
    self._add_error("invalid_price", f"Cannot parse price: {price_text}")
    price = 0.0
```

### 4. Default Values
Follow the requirements for default values:
- Empty string for missing text fields
- Empty array for missing lists
- 0.0 for missing prices
- False for missing booleans

## Testing

The base scraper includes comprehensive tests:

```python
# Run all scraper tests
python tests/test_base_scraper.py

# Run specific test
python -m unittest tests.test_base_scraper.TestBaseScraper.test_json_output_structure
```

## File Output

Generated files follow this naming convention:
```
{domain}_{timestamp}.json
```

Example: `foody_com_cy_20250711_234704.json`

Files are saved to the `output/` directory by default with UTF-8 encoding and 2-space indentation for readability.
