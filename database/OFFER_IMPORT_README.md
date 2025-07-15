# Offer Import Logic Implementation

This implementation adds comprehensive offer management to the scraper database system.

## 🎯 What's New

### 1. Enhanced Data Import (`import_data.py`)
- **Automatic offer extraction** from scraped product data
- **Links products to offers** via `offer_id` foreign key
- **Creates unique offer records** in the `offers` table
- **Processes discount percentages** and offer names

### 2. Migration Script (`migrate_existing_offers.py`)
- **Processes existing JSON files** to extract historical offers
- **Populates offers table** with historical data
- **Analyze mode** to preview offers without importing

### 3. Offer Management Utilities (`offer_utils.py`)
- **List and monitor offers** across all restaurants
- **Get offer statistics** and analytics
- **Cleanup inactive offers** automatically
- **Simple command-line interface**

## 🚀 Quick Start

### 1. Import New Data (Automatic Offer Processing)
```bash
# Import a single file (offers will be automatically extracted)
python import_data.py --file ../output/foody_costa-coffee.json

# Import entire directory
python import_data.py --directory ../output/
```

### 2. Migrate Existing Data
```bash
# Analyze offers in a file first
python migrate_existing_offers.py --file ../output/foody_costa-coffee.json --analyze-only

# Migrate existing files to populate offers table
python migrate_existing_offers.py --directory ../output/
```

### 3. Monitor Offers
```bash
# Show offer statistics
python offer_utils.py offer-stats

# List all active offers
python offer_utils.py active-offers

# List offers for specific restaurant
python offer_utils.py list-offers --restaurant "Costa Coffee"

# Cleanup inactive offers
python offer_utils.py cleanup-inactive --days 30
```

## 📊 How Offer Processing Works

### Data Flow
```
Scraped JSON → Extract Offers → Create Offer Records → Link to Products
     ↓              ↓                    ↓                   ↓
{offer_name,    Unique offers     offers table      product_prices
 discount_%}    identified        populated         linked via offer_id
```

### Offer Extraction Logic
1. **Scan all products** for `offer_name` and `discount_percentage`
2. **Create unique offers** based on offer name per restaurant
3. **Link products** to offers via `offer_id` foreign key
4. **Set offer metadata**: type, discount percentage, start date

### Example Transformation
**Input (JSON):**
```json
{
  "products": [
    {
      "name": "Cappuccino",
      "price": 2.40,
      "original_price": 3.00,
      "offer_name": "20% off Hot Drinks",
      "discount_percentage": 20
    }
  ]
}
```

**Output (Database):**
```sql
-- offers table
INSERT INTO offers (restaurant_id, name, discount_percentage, offer_type, is_active)
VALUES ('rest-uuid', '20% off Hot Drinks', 20, 'percentage', true);

-- product_prices table (with offer link)
INSERT INTO product_prices (product_id, price, original_price, offer_id, offer_name)
VALUES ('prod-uuid', 2.40, 3.00, 'offer-uuid', '20% off Hot Drinks');
```

## 🎛️ Grafana Integration

With populated offers table, your Grafana queries now work:

```sql
-- Active offers with product counts
SELECT 
    $__time(o.created_at),
    o.name as "Offer Name",
    r.name as "Restaurant",
    o.discount_percentage as "Discount %",
    COUNT(pp.id) as "Products Affected"
FROM offers o
JOIN restaurants r ON o.restaurant_id = r.id
LEFT JOIN product_prices pp ON o.id = pp.offer_id
WHERE o.is_active = true
    AND o.created_at BETWEEN $__timeFrom() AND $__timeTo()
GROUP BY o.id, o.name, r.name, o.discount_percentage, o.created_at
ORDER BY o.created_at DESC
```

## 📈 Benefits

### Before (Empty Offers Table)
- ❌ No offer tracking
- ❌ Manual offer analysis required
- ❌ No historical offer data
- ❌ Grafana queries return empty

### After (Populated Offers Table)
- ✅ **Automatic offer extraction** from scraped data
- ✅ **Complete offer lifecycle tracking** (start/end dates)
- ✅ **Historical offer analysis** and trends
- ✅ **Grafana dashboards** showing live offer data
- ✅ **Product-to-offer linking** for detailed analysis
- ✅ **Competitive intelligence** on discount strategies

## 🔧 Advanced Usage

### Custom Offer Processing
```python
# In your scraper code, ensure offer data is included:
product_data = {
    "name": "Product Name",
    "price": 10.00,
    "original_price": 12.50,
    "offer_name": "Early Bird Special",  # Key field for offer extraction
    "discount_percentage": 20            # Key field for offer processing
}
```

### Offer Cleanup Automation
```bash
# Add to cron job for automatic cleanup
0 2 * * * cd /path/to/database && python offer_utils.py cleanup-inactive --days 14
```

### Custom Queries
```sql
-- Find restaurants with most aggressive discounting
SELECT 
    r.name,
    AVG(o.discount_percentage) as avg_discount,
    COUNT(o.id) as total_offers
FROM offers o
JOIN restaurants r ON o.restaurant_id = r.id
WHERE o.is_active = true
GROUP BY r.name
ORDER BY avg_discount DESC;

-- Offer timeline analysis
SELECT 
    DATE_TRUNC('day', created_at) as offer_date,
    COUNT(*) as offers_started
FROM offers
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY offer_date;
```

## 🐛 Troubleshooting

### Common Issues

**Issue: Offers table still empty after import**
```bash
# Check if offer_name fields exist in JSON
python migrate_existing_offers.py --file your_file.json --analyze-only
```

**Issue: Duplicate offers created**
```sql
-- Check for duplicates
SELECT restaurant_id, name, COUNT(*) 
FROM offers 
GROUP BY restaurant_id, name 
HAVING COUNT(*) > 1;
```

**Issue: Products not linked to offers**
```sql
-- Check offer linkage
SELECT 
    COUNT(*) as total_prices,
    COUNT(offer_id) as linked_to_offers
FROM product_prices;
```

## 📝 Next Steps

1. **Run migration** on existing data: `python migrate_existing_offers.py --directory ../output/`
2. **Check results**: `python offer_utils.py offer-stats`
3. **Update Grafana** dashboards with new offer queries
4. **Set up monitoring** for offer lifecycle events
5. **Configure cleanup** automation for inactive offers

Your offers table will now be populated and ready for competitive analysis! 🎉
