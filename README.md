# Food Delivery Aggregator & Menu Scraper

A comprehensive web scraping system for food delivery platforms with PostgreSQL time-series data storage and business intelligence capabilities.

## 🚀 **Current Status**

✅ **Production-Ready Features:**
- **Foody Scraper**: Complete implementation for foody.com.cy
- **Wolt Scraper**: Complete implementation for wolt.com 
- **Database System**: PostgreSQL schema with time-series price tracking
- **Scraper Tracking**: Platform identification (foody vs wolt) for business intelligence
- **Data Import**: Automated JSON-to-database pipeline
- **431+ Products**: Successfully scraped from 4 restaurants across both platforms

## 🎯 **Key Capabilities**

### 🕷️ **Multi-Platform Scraping**
- **Foody.com.cy**: HTTP-based scraper with BeautifulSoup
- **Wolt.com**: Selenium-based scraper for JavaScript-heavy sites
- **Unified Output**: Consistent JSON format across all platforms
- **Error Handling**: Comprehensive logging and retry mechanisms

### 🗄️ **Advanced Database System**
- **Time-Series Data**: Track price changes over time
- **Scraper Tracking**: Filter data by platform (foody vs wolt)
- **Business Intelligence**: Compare pricing strategies between platforms
- **Performance Optimized**: Indexed for fast queries on 431+ products

### 📊 **Business Intelligence Queries**
```sql
-- Filter by scraper platform
SELECT * FROM current_product_prices WHERE scraper_name = 'wolt';
SELECT * FROM current_product_prices WHERE scraper_name = 'foody';

-- Compare pricing between platforms
SELECT scraper_name, AVG(price), COUNT(*) 
FROM current_product_prices 
GROUP BY scraper_name;

-- Track price history with scraper context
SELECT * FROM product_price_history 
WHERE scraper_name = 'foody' AND restaurant_name = 'Costa Coffee';
```

## 📁 **Project Structure**

```
scraper-copilot/
├── src/
│   ├── common/                    # Core scraping framework
│   │   ├── config.py             # Configuration management
│   │   ├── factory.py            # Scraper factory pattern
│   │   ├── base_scraper.py       # Abstract base scraper
│   │   └── logging_config.py     # Logging setup
│   └── scrapers/                 # Platform implementations
│       ├── foody_scraper.py      # ✅ Foody.com.cy scraper
│       └── wolt_scraper.py       # ✅ Wolt.com scraper
├── database/                     # Database infrastructure
│   ├── init_schema.sql          # ✅ Complete PostgreSQL schema
│   ├── import_data.py           # ✅ JSON to database importer
│   ├── .env.example             # Database configuration template
│   ├── setup_db.py              # Database initialization
│   ├── example_queries.sql      # Sample business intelligence queries
│   └── requirements.txt         # Database dependencies
├── scrapers/                    # Configuration files
│   ├── foody.md                 # Foody scraper configuration
│   ├── foody_com.md             # Alternative foody config
│   └── template.md              # Configuration template
├── output/                      # Scraping output (JSON files)
├── tests/                       # Unit tests
└── test_scraper_filtering.py    # ✅ Database filtering tests
```

## 🚀 **Quick Start**

### 1. **Set Up Environment**
```bash
# Install Python dependencies
pip install -r requirements.txt
pip install -r database/requirements.txt

# Set up database configuration
cp database/.env.example database/.env
# Edit database/.env with your PostgreSQL credentials
```

### 2. **Initialize Database**
```bash
# Create database schema
python database/setup_db.py

# The schema includes:
# - 9 tables with scraper tracking
# - 4 views for business intelligence
# - Time-series price tracking
# - Performance indexes
```

### 3. **Run Scrapers**
```bash
# Scrape Foody restaurants
python -m src.scrapers.foody_scraper

# Scrape Wolt restaurants  
python -m src.scrapers.wolt_scraper

# Output saved to output/ directory as JSON
```

### 4. **Import Data to Database**
```bash
# Import all JSON files
python database/import_data.py --directory output/

# Import specific file
python database/import_data.py --file output/foody_costa-coffee.json
```

### 5. **Test Database Functionality**
```bash
# Test scraper filtering capabilities
python test_scraper_filtering.py

# Sample output:
# foody: 216 products from 2 restaurants
# wolt: 215 products from 2 restaurants
```

## 🗄️ **Database Schema**

### **Core Tables**
- `scrapers` - Track scraper implementations (foody, wolt)
- `domains` - Delivery platforms with scraper relationships
- `restaurants` - Unique restaurants across all platforms
- `products` - Product information with categories
- `product_prices` - Time-series pricing data
- `scraping_sessions` - Metadata about each scrape run

### **Business Intelligence Views**
- `current_product_prices` - Latest prices with scraper information
- `restaurant_latest_stats` - Restaurant statistics by platform
- `product_price_history` - Complete price history with trends
- `active_offers` - Current promotions and discounts

### **Sample Data (Current)**
- **4 Restaurants**: Costa Coffee, Pasta Strada, KFC Engomi, Wagamama
- **431 Products**: Full menu items with pricing
- **2 Platforms**: Foody.com.cy and Wolt.com
- **Time-Series**: Price tracking with scraper identification

## 🕷️ **Scraper Implementations**

### **FoodyScraper** (`src/scrapers/foody_scraper.py`)
- ✅ **HTTP-based**: Uses requests + BeautifulSoup
- ✅ **Fast Performance**: ~3 seconds per restaurant
- ✅ **Rate Limiting**: Respectful scraping practices
- ✅ **Error Handling**: Retry logic with exponential backoff
- ✅ **Live Data**: Successfully scraped Costa Coffee, Pasta Strada

### **WoltScraper** (`src/scrapers/wolt_scraper.py`)
- ✅ **Selenium-based**: Handles JavaScript-heavy sites
- ✅ **Robust Navigation**: Waits for dynamic content loading
- ✅ **Category Processing**: Extracts complete menu structures
- ✅ **Anti-Bot Handling**: Manages bot detection and rate limiting
- ✅ **Live Data**: Successfully scraped KFC Engomi, Wagamama

## 📊 **Business Intelligence Examples**

### **Platform Comparison**
```sql
-- Compare average prices between platforms
SELECT 
    scraper_name,
    COUNT(DISTINCT restaurant_name) as restaurants,
    COUNT(*) as total_products,
    ROUND(AVG(price), 2) as avg_price,
    ROUND(MIN(price), 2) as min_price,
    ROUND(MAX(price), 2) as max_price
FROM current_product_prices 
GROUP BY scraper_name;

-- Results:
-- foody: 2 restaurants, 216 products, avg €4.85
-- wolt: 2 restaurants, 215 products, avg €6.96
```

### **Restaurant Analysis**
```sql
-- Find restaurants available on multiple platforms
SELECT restaurant_name, 
       array_agg(DISTINCT scraper_name) as platforms,
       COUNT(DISTINCT scraper_name) as platform_count
FROM current_product_prices 
GROUP BY restaurant_name 
HAVING COUNT(DISTINCT scraper_name) > 1;
```

### **Price Trend Analysis**
```sql
-- Track price changes over time
SELECT product_name, restaurant_name, scraper_name,
       price, previous_price, price_change, scraped_at
FROM product_price_history 
WHERE price_change IS NOT NULL
ORDER BY ABS(price_change) DESC
LIMIT 10;
```

## 🧪 **Testing & Quality Assurance**

### **Unit Tests**
```bash
# Run configuration tests
python -m pytest tests/test_config.py -v

# Run scraper tests  
python tests/test_base_scraper.py
```

### **Database Tests**
```bash
# Test scraper filtering functionality
python test_scraper_filtering.py

# Test data import pipeline
python database/import_data.py --file output/test_file.json
```

### **Live Scraping Tests**
```bash
# Test Foody scraper
python demo_foody_scraper.py

# Test Wolt scraper with specific restaurant
python -m src.scrapers.wolt_scraper --url "https://wolt.com/en/cyp/limassol/restaurant/kfc-engomi"
```

## 🔧 **Configuration System**

The project uses a flexible configuration system supporting multiple formats:

### **Simple Configuration** (`scrapers/foody.md`)
```markdown
### base_url
`https://foody.com.cy`

### item_selector
`.product-item`

### requires_javascript
`false`
```

### **Detailed Configuration** (`scrapers/template.md`)
```markdown
# Website Scraper Configuration

## Scraping Strategy
- **Method**: Selenium
- **JavaScript Required**: Yes
- **Anti-Bot Protection**: CloudFlare, Rate limiting

## Selectors
- **Products**: `[data-testid="product-card"]`
- **Prices**: `.price-display`
```

## 🚀 **Next Steps & Roadmap**

### **Immediate Priorities**
- [ ] Add more restaurants (expand to 10+ restaurants per platform)
- [ ] Implement price change alerts and notifications
- [ ] Add data visualization dashboard
- [ ] Create REST API for external access

### **Platform Expansion**
- [ ] Efood.gr scraper implementation
- [ ] Foodpanda scraper for additional markets
- [ ] Delivery Hero platform integration

### **Advanced Features**
- [ ] Machine learning price prediction models
- [ ] Automated competitive analysis reports
- [ ] Real-time price monitoring with webhooks
- [ ] Multi-city expansion support

## 🤝 **Contributing**

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-scraper`
3. **Add scraper implementation**: Follow `BaseScraper` pattern
4. **Add configuration**: Create `.md` file in `scrapers/`
5. **Test thoroughly**: Run existing tests + add new ones
6. **Submit pull request**: Include database schema updates if needed

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

---

**🎯 Production Status**: Ready for live data collection with 431+ products across 4 restaurants on 2 platforms with comprehensive database tracking and business intelligence capabilities.
