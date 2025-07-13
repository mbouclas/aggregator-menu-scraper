# Foody Offer Name Extraction Feature

## Summary

This feature adds support for extracting named offers (like "1+1 Deals", "Foody deals", "8€ meals") from foody.com.cy product pages. The feature distinguishes between percentage-based discounts and named promotional offers, storing only the named offers in the database.

## Branch Information

- **Branch**: `feature/foody-offer-names`
- **Target**: Foody scraper only (as requested)
- **Commit**: bc8546e

## Implementation Details

### 1. Offer Detection Logic

The feature looks for offers in HTML elements matching the pattern provided by the user:

```html
<span class="sn-title_522dc0">1+1 Deals</span>
<span class="sn-title_522dc0">Foody deals</span>
<span class="sn-title_522dc0">8€ meals</span>
```

### 2. Key Distinction

**✅ Extracted as offer names:**
- `1+1 Deals`
- `Foody deals` 
- `8€ meals`
- `Summer Special`
- Any text without `%` symbol

**❌ Ignored (percentage discounts):**
- `up to -37%`
- `50% off`
- `-25%`
- Any text containing `%` symbol

### 3. Files Modified

1. **`src/scrapers/foody_scraper.py`**
   - Added `_extract_offer_name()` method
   - Added `offer_name` field to product data structure
   - Integrated offer extraction into `_extract_single_product()`

2. **`src/scrapers/fast_foody_scraper.py`**
   - Added `_extract_offer_name_fast()` method for performance-optimized extraction
   - Added `offer_name` field to product data structure
   - Integrated offer extraction into `_extract_single_product_fast()`

3. **`docs/FoodyScraper.md`**
   - Updated documentation to reflect new feature
   - Added offer processing section

4. **`test_offer_extraction.py`** (new file)
   - Comprehensive test suite with 6 test cases
   - Validates extraction logic with user-provided examples
   - Demonstrates expected behavior

### 4. Database Integration

The database schema already supports offer names:

```sql
-- In product_prices table (line 129 of init_schema.sql)
offer_name VARCHAR(255), -- Name of applied offer (for future iterations)
```

The import logic in `database/import_data.py` already handles the `offer_name` field:

```python
# Line 365 in import_data.py
product_data.get('offer_name'),  # Future field
```

### 5. Data Flow

```
HTML Page → Scraper → Extract Offer Name → Product Data → Database
            ↓
    <span class="sn-title_522dc0">1+1 Deals</span>
            ↓
    offer_name: "1+1 Deals"
            ↓
    product_prices.offer_name = "1+1 Deals"
```

### 6. Test Results

All tests pass successfully:

```
✓ Test 1: 1+1 Deals offer
✓ Test 2: Foody deals offer  
✓ Test 3: 8€ meals offer
✓ Test 4: Percentage discount (should be ignored)
✓ Test 5: Another percentage (should be ignored)
✓ Test 6: Complex offer container
```

## Usage

After this feature is deployed, offer names will automatically be extracted and stored in the database when scraping foody.com.cy restaurants. The data can be queried to:

1. Track promotional campaigns by restaurant
2. Analyze offer effectiveness over time
3. Identify popular offer types
4. Generate reports on promotional activity

## Example Output

Products with offers will now include the `offer_name` field:

```json
{
  "id": "foody_prod_123",
  "name": "Freddo Espresso",
  "description": "Cold espresso coffee",
  "price": 3.50,
  "original_price": 3.50,
  "currency": "EUR",
  "discount_percentage": 0.0,
  "offer_name": "1+1 Deals",
  "category": "Cold Coffees",
  "image_url": "",
  "availability": true,
  "options": []
}
```

## Testing

To test the feature:

1. Run the test suite: `python test_offer_extraction.py`
2. Run a foody scraper on a restaurant with named offers
3. Check the JSON output for `offer_name` fields
4. Verify data is stored in `product_prices.offer_name` column

## Performance Impact

- **Minimal**: The offer extraction adds one additional DOM query per product
- **Fast Scraper**: Optimized version with single selector and quick validation
- **No breaking changes**: Existing functionality remains unchanged
