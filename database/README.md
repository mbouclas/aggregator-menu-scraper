# Scraper Database Setup

This directory contains the complete database schema and tools for storing and analyzing scraper data with time series price tracking and offer management.

## Files Overview

- **`init_schema.sql`** - Complete database schema initialization
- **`example_queries.sql`** - 24 example queries for data analysis
- **`import_data.py`** - Python script to import JSON scraper output into database

## Quick Setup

### 1. Initialize PostgreSQL Database

```bash
# Create database
createdb scraper_db

# Initialize schema
psql scraper_db -f database/init_schema.sql
```

### 2. Install Python Dependencies

```bash
pip install psycopg2-binary
```

### 3. Import Scraper Data

```bash
# Import single file
python database/import_data.py --file output/foody_costa-coffee.json

# Import all files in directory
python database/import_data.py --directory output/

# Custom connection string
python database/import_data.py --file output/wolt_kfc-engomi.json --connection "postgresql://user:pass@localhost/scraper_db"
```

## Database Schema Overview

### Core Tables

| Table | Purpose | Key Features |
|-------|---------|-------------|
| `domains` | Delivery platforms (foody.com.cy, wolt.com) | Base URLs, display names |
| `restaurants` | Unique restaurants across platforms | Name, brand, cuisine types |
| `restaurant_domains` | Restaurant presence on platforms | Many-to-many relationship |
| `categories` | Product categories per restaurant | Display order, source tracking |
| `products` | Base product information | External IDs, descriptions, options |

### Time Series Tables

| Table | Purpose | Key Features |
|-------|---------|-------------|
| `product_prices` | **Price history over time** | Price, discounts, offers, scraped timestamps |
| `restaurant_snapshots` | Restaurant metadata history | Delivery fees, ratings, product counts |
| `scraping_sessions` | Scrape run metadata | Performance tracking, error logging |

### Offers & Promotions

| Table | Purpose | Key Features |
|-------|---------|-------------|
| `offers` | Promotional campaigns | Discount types, start/end dates, descriptions |
| `product_prices.offer_name` | Applied offer tracking | Links products to specific offers |

## Key Views

- **`current_product_prices`** - Latest price for each active product
- **`restaurant_latest_stats`** - Most recent restaurant statistics  
- **`product_price_history`** - Complete price history with change calculations
- **`active_offers`** - Currently running promotions

## Example Queries

### Find Products with Biggest Discounts
```sql
SELECT 
    restaurant_name,
    product_name,
    original_price,
    price,
    discount_percentage,
    (original_price - price) as savings
FROM current_product_prices 
WHERE discount_percentage > 0
ORDER BY discount_percentage DESC
LIMIT 10;
```

### Track Price Changes Over Time
```sql
SELECT 
    product_name,
    restaurant_name,
    price,
    scraped_at,
    LAG(price) OVER (ORDER BY scraped_at) as previous_price
FROM product_price_history 
WHERE product_name = 'Freddo Espresso Primo'
ORDER BY scraped_at DESC;
```

### Find Recently Started Offers
```sql
SELECT 
    restaurant_name,
    product_name,
    offer_name,
    discount_percentage,
    scraped_at as offer_started
FROM product_price_history
WHERE offer_name IS NOT NULL
    AND scraped_at >= NOW() - INTERVAL '7 days'
ORDER BY scraped_at DESC;
```

## Advanced Features

### Custom Functions

```sql
-- Get price trend for specific product
SELECT * FROM get_product_price_trend(
    (SELECT id FROM products WHERE name = 'Freddo Espresso Primo' LIMIT 1),
    30  -- days back
);

-- Find recent price changes
SELECT * FROM find_recent_price_changes(7);  -- last 7 days
```

### Time Series Analysis

The schema is optimized for time series queries:

- **Price volatility tracking** - Identify products with frequent price changes
- **Offer duration analysis** - Track how long promotions run
- **Market competitiveness** - Compare prices across restaurants
- **Seasonal trends** - Analyze price patterns over time

### Performance Optimizations

- **Trigram indexes** on product names for fuzzy search
- **Composite indexes** on (product_id, scraped_at) for time series queries
- **Partial indexes** on discounted products only
- **JSONB fields** for flexible options and error storage

## Import Process

The `import_data.py` script handles:

1. **Domain management** - Auto-creates delivery platforms
2. **Restaurant deduplication** - Unique restaurants across platforms  
3. **Category mapping** - Links products to categories
4. **Price history** - Time series price tracking
5. **Session tracking** - Performance and error monitoring
6. **Data validation** - Handles missing fields gracefully

### Usage Examples

```bash
# Import with verbose logging
python database/import_data.py --file output/foody_costa-coffee.json --verbose

# Import entire output directory
python database/import_data.py --directory output/

# Custom database connection
python database/import_data.py --file output/wolt_kfc-engomi.json \
    --connection "postgresql://scraper_user:password@db.example.com:5432/scraper_production"
```

## Monitoring & Maintenance

### Data Quality Checks

Run example query #23 to check for data inconsistencies:
- Products without prices
- Negative prices  
- Discounts exceeding original price
- Missing restaurant names

### Performance Monitoring

Run example query #24 to monitor:
- Table sizes and growth
- Insert/update/delete statistics
- Index usage patterns

### Regular Maintenance

```sql
-- Analyze tables for query optimization
ANALYZE;

-- Vacuum to reclaim space
VACUUM;

-- Reindex if needed
REINDEX DATABASE scraper_db;
```

## Future Enhancements

The schema is designed to support:

- **Named offers** - Already has `offer_name` field ready
- **Product variants** - JSONB options field for sizes, flavors, etc.
- **Image tracking** - Image URL changes over time
- **Location-based pricing** - Restaurant address field for geo-analysis
- **User ratings** - Can be added to restaurant_snapshots
- **Inventory tracking** - Availability field in product_prices

## Troubleshooting

### Common Issues

1. **Connection failed** - Check PostgreSQL is running and connection string
2. **Permission denied** - Ensure database user has CREATE/INSERT privileges  
3. **JSON parsing errors** - Validate JSON files are properly formatted
4. **Duplicate key errors** - Check for existing data with same timestamps

### Debug Mode

```bash
python database/import_data.py --file output/test.json --verbose
```

This enables detailed logging of the import process.

---

For more complex queries and analysis examples, see `example_queries.sql` which contains 24 different query patterns for business intelligence and data analysis.
