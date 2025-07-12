-- =====================================================
-- SCRAPER DATABASE - EXAMPLE QUERIES
-- =====================================================
-- Common queries for analyzing scraper data
-- =====================================================

-- =====================================================
-- BASIC DATA RETRIEVAL
-- =====================================================

-- 1. Get all restaurants with their latest stats
SELECT 
    restaurant_name,
    brand,
    domain_name,
    total_products,
    total_categories,
    delivery_fee,
    minimum_order,
    rating,
    scraped_at
FROM restaurant_latest_stats
ORDER BY restaurant_name, domain_name;

-- 2. Get all current products for a specific restaurant
SELECT 
    product_name as name,
    category_name as category,
    price,
    original_price,
    discount_percentage,
    availability,
    is_discounted
FROM current_product_prices 
WHERE restaurant_name = 'Costa Coffee'
ORDER BY category_name, product_name;

-- 3. Get products by category across all restaurants
SELECT 
    restaurant_name,
    product_name,
    price,
    original_price,
    discount_percentage
FROM current_product_prices 
WHERE category_name = 'Cold Coffees'
ORDER BY price DESC;

-- =====================================================
-- PRICE ANALYSIS
-- =====================================================

-- 4. Find products with the highest discounts currently
SELECT 
    restaurant_name,
    product_name,
    category_name,
    original_price,
    price,
    discount_percentage,
    (original_price - price) as savings_amount
FROM current_product_prices 
WHERE discount_percentage > 0
ORDER BY discount_percentage DESC, savings_amount DESC
LIMIT 20;

-- 5. Compare prices of same product across restaurants
SELECT 
    product_name,
    restaurant_name,
    price,
    original_price,
    discount_percentage,
    RANK() OVER (PARTITION BY product_name ORDER BY price) as price_rank
FROM current_product_prices 
WHERE product_name ILIKE '%latte%'
ORDER BY product_name, price;

-- 6. Get price history for a specific product
SELECT 
    product_name,
    restaurant_name,
    price,
    original_price,
    discount_percentage,
    offer_name,
    scraped_at,
    price_change,
    CASE 
        WHEN price_change > 0 THEN '📈 UP'
        WHEN price_change < 0 THEN '📉 DOWN'
        ELSE '➡️ STABLE'
    END as trend_indicator
FROM product_price_history 
WHERE product_name = 'Freddo Espresso Primo'
    AND restaurant_name = 'Costa Coffee'
ORDER BY scraped_at DESC
LIMIT 10;

-- =====================================================
-- TIME SERIES ANALYSIS
-- =====================================================

-- 7. Track price changes over time for all products
SELECT 
    DATE(scraped_at) as date,
    COUNT(*) as total_products_scraped,
    COUNT(*) FILTER (WHERE discount_percentage > 0) as discounted_products,
    AVG(price) as avg_price,
    AVG(discount_percentage) as avg_discount,
    COUNT(DISTINCT restaurant_name) as restaurants_scraped
FROM product_price_history
WHERE scraped_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(scraped_at)
ORDER BY date DESC;

-- 8. Find products that recently went on sale
SELECT 
    restaurant_name,
    product_name,
    category_name,
    price,
    original_price,
    discount_percentage,
    offer_name,
    scraped_at as sale_started
FROM product_price_history
WHERE discount_percentage > 0
    AND previous_price = original_price  -- Was full price before
    AND scraped_at >= NOW() - INTERVAL '7 days'
ORDER BY scraped_at DESC, discount_percentage DESC;

-- 9. Find products that recently increased in price
SELECT 
    restaurant_name,
    product_name,
    category_name,
    previous_price as old_price,
    price as new_price,
    price_change,
    ROUND((price_change / previous_price * 100)::numeric, 2) as increase_percentage,
    scraped_at as price_change_date
FROM product_price_history
WHERE price_change > 0
    AND scraped_at >= NOW() - INTERVAL '7 days'
ORDER BY increase_percentage DESC
LIMIT 20;

-- =====================================================
-- OFFER AND DISCOUNT ANALYSIS
-- =====================================================

-- 10. Analyze offer duration and effectiveness
WITH offer_periods AS (
    SELECT 
        restaurant_name,
        offer_name,
        MIN(scraped_at) as offer_start,
        MAX(scraped_at) as offer_end,
        COUNT(DISTINCT product_id) as products_affected,
        AVG(discount_percentage) as avg_discount,
        COUNT(*) as total_observations
    FROM product_price_history
    WHERE offer_name IS NOT NULL
    GROUP BY restaurant_name, offer_name
)
SELECT 
    restaurant_name,
    offer_name,
    offer_start,
    offer_end,
    (offer_end - offer_start) as offer_duration,
    products_affected,
    ROUND(avg_discount::numeric, 2) as avg_discount_percent,
    total_observations
FROM offer_periods
ORDER BY offer_start DESC;

-- 11. Find most frequent discount percentages
SELECT 
    discount_percentage,
    COUNT(*) as frequency,
    COUNT(DISTINCT product_id) as unique_products,
    COUNT(DISTINCT restaurant_name) as restaurants_using,
    ROUND(AVG(price)::numeric, 2) as avg_discounted_price
FROM product_price_history
WHERE discount_percentage > 0
GROUP BY discount_percentage
HAVING COUNT(*) > 5  -- Only show common discounts
ORDER BY frequency DESC;

-- =====================================================
-- RESTAURANT ANALYSIS
-- =====================================================

-- 12. Restaurant comparison by pricing
SELECT 
    restaurant_name,
    brand,
    COUNT(*) as total_products,
    ROUND(AVG(price)::numeric, 2) as avg_price,
    ROUND(MIN(price)::numeric, 2) as min_price,
    ROUND(MAX(price)::numeric, 2) as max_price,
    COUNT(*) FILTER (WHERE discount_percentage > 0) as products_on_sale,
    ROUND(AVG(discount_percentage) FILTER (WHERE discount_percentage > 0)::numeric, 2) as avg_discount
FROM current_product_prices
GROUP BY restaurant_name, brand
ORDER BY avg_price DESC;

-- 13. Find restaurants with most active promotions
SELECT 
    restaurant_name,
    COUNT(DISTINCT offer_name) as active_offers,
    COUNT(*) FILTER (WHERE discount_percentage > 0) as discounted_products,
    ROUND(AVG(discount_percentage) FILTER (WHERE discount_percentage > 0)::numeric, 2) as avg_discount,
    MAX(discount_percentage) as max_discount
FROM current_product_prices
GROUP BY restaurant_name
HAVING COUNT(*) FILTER (WHERE discount_percentage > 0) > 0
ORDER BY discounted_products DESC, avg_discount DESC;

-- =====================================================
-- CATEGORY ANALYSIS
-- =====================================================

-- 14. Price analysis by category
SELECT 
    category_name,
    COUNT(*) as product_count,
    ROUND(AVG(price)::numeric, 2) as avg_price,
    ROUND(MIN(price)::numeric, 2) as min_price,
    ROUND(MAX(price)::numeric, 2) as max_price,
    COUNT(*) FILTER (WHERE discount_percentage > 0) as discounted_items,
    ROUND(AVG(discount_percentage) FILTER (WHERE discount_percentage > 0)::numeric, 2) as avg_discount
FROM current_product_prices
GROUP BY category_name
ORDER BY avg_price DESC;

-- 15. Find categories with most price volatility
SELECT 
    category_name,
    COUNT(DISTINCT product_id) as unique_products,
    COUNT(*) as total_price_points,
    ROUND(AVG(price_change)::numeric, 3) as avg_price_change,
    ROUND(STDDEV(price_change)::numeric, 3) as price_volatility,
    COUNT(*) FILTER (WHERE price_change != 0) as products_with_changes
FROM product_price_history
WHERE scraped_at >= NOW() - INTERVAL '30 days'
    AND price_change IS NOT NULL
GROUP BY category_name
HAVING COUNT(DISTINCT product_id) >= 5  -- Categories with enough products
ORDER BY price_volatility DESC NULLS LAST;

-- =====================================================
-- SCRAPING PERFORMANCE
-- =====================================================

-- 16. Scraping session analysis
SELECT 
    DATE(started_at) as scrape_date,
    domain_name,
    COUNT(*) as total_sessions,
    COUNT(*) FILTER (WHERE status = 'completed') as successful_sessions,
    SUM(product_count) as total_products_scraped,
    AVG(duration_seconds) as avg_duration_seconds,
    SUM(error_count) as total_errors
FROM scraping_sessions ss
JOIN domains d ON ss.domain_id = d.id
WHERE started_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(started_at), domain_name
ORDER BY scrape_date DESC, domain_name;

-- 17. Find scraping issues
SELECT 
    r.name as restaurant_name,
    d.name as domain_name,
    ss.url,
    ss.started_at,
    ss.status,
    ss.error_count,
    ss.duration_seconds,
    ss.errors
FROM scraping_sessions ss
JOIN restaurants r ON ss.restaurant_id = r.id
JOIN domains d ON ss.domain_id = d.id
WHERE ss.error_count > 0 OR ss.status != 'completed'
ORDER BY ss.started_at DESC
LIMIT 20;

-- =====================================================
-- BUSINESS INTELLIGENCE QUERIES
-- =====================================================

-- 18. Price competitiveness analysis
WITH product_prices_ranked AS (
    SELECT 
        product_name,
        restaurant_name,
        price,
        RANK() OVER (PARTITION BY product_name ORDER BY price) as price_rank,
        COUNT(*) OVER (PARTITION BY product_name) as restaurant_count
    FROM current_product_prices
    WHERE product_name IN (
        SELECT product_name 
        FROM current_product_prices 
        GROUP BY product_name 
        HAVING COUNT(DISTINCT restaurant_name) >= 2
    )
)
SELECT 
    product_name,
    restaurant_name,
    price,
    CASE 
        WHEN price_rank = 1 THEN '🥇 CHEAPEST'
        WHEN price_rank = restaurant_count THEN '💰 MOST EXPENSIVE'
        ELSE '🔸 MIDDLE'
    END as price_position
FROM product_prices_ranked
ORDER BY product_name, price;

-- 19. Market share by price ranges
SELECT 
    CASE 
        WHEN price < 2 THEN '€0-2'
        WHEN price < 5 THEN '€2-5'
        WHEN price < 10 THEN '€5-10'
        WHEN price < 20 THEN '€10-20'
        ELSE '€20+'
    END as price_range,
    COUNT(*) as product_count,
    ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER())::numeric, 2) as percentage,
    COUNT(DISTINCT restaurant_name) as restaurants_in_range
FROM current_product_prices
GROUP BY 
    CASE 
        WHEN price < 2 THEN '€0-2'
        WHEN price < 5 THEN '€2-5'
        WHEN price < 10 THEN '€5-10'
        WHEN price < 20 THEN '€10-20'
        ELSE '€20+'
    END
ORDER BY MIN(price);

-- 20. Identify products that are always on sale
SELECT 
    restaurant_name,
    product_name,
    category_name,
    COUNT(*) as times_scraped,
    COUNT(*) FILTER (WHERE discount_percentage > 0) as times_on_sale,
    ROUND((COUNT(*) FILTER (WHERE discount_percentage > 0) * 100.0 / COUNT(*))::numeric, 2) as sale_percentage,
    MIN(price) as lowest_price,
    MAX(original_price) as highest_original_price,
    AVG(discount_percentage) as avg_discount
FROM product_price_history
WHERE scraped_at >= NOW() - INTERVAL '30 days'
GROUP BY restaurant_name, product_name, category_name
HAVING COUNT(*) >= 5  -- At least 5 scrapes
    AND (COUNT(*) FILTER (WHERE discount_percentage > 0) * 100.0 / COUNT(*)) >= 80  -- On sale 80%+ of time
ORDER BY sale_percentage DESC, avg_discount DESC;

-- =====================================================
-- USING THE CUSTOM FUNCTIONS
-- =====================================================

-- 21. Get price trend for a specific product
SELECT * FROM get_product_price_trend(
    (SELECT id FROM products WHERE name = 'Freddo Espresso Primo' LIMIT 1),
    30  -- Last 30 days
);

-- 22. Find recent price changes
SELECT * FROM find_recent_price_changes(7);  -- Last 7 days

-- =====================================================
-- DATA QUALITY CHECKS
-- =====================================================

-- 23. Check for data consistency issues
SELECT 
    'Products without prices' as issue_type,
    COUNT(*) as count
FROM products p
LEFT JOIN product_prices pp ON p.id = pp.product_id
WHERE pp.id IS NULL AND p.is_active = true

UNION ALL

SELECT 
    'Negative prices' as issue_type,
    COUNT(*) as count
FROM product_prices
WHERE price < 0

UNION ALL

SELECT 
    'Discount > original price' as issue_type,
    COUNT(*) as count
FROM product_prices
WHERE price > original_price

UNION ALL

SELECT 
    'Missing restaurant names' as issue_type,
    COUNT(*) as count
FROM restaurants
WHERE name IS NULL OR name = '';

-- =====================================================
-- PERFORMANCE MONITORING
-- =====================================================

-- 24. Check table sizes and growth
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_stat_get_tuples_inserted(c.oid) as inserts,
    pg_stat_get_tuples_updated(c.oid) as updates,
    pg_stat_get_tuples_deleted(c.oid) as deletes
FROM pg_tables pt
JOIN pg_class c ON c.relname = pt.tablename
WHERE schemaname = 'public'
    AND tablename IN ('products', 'product_prices', 'restaurants', 'categories', 'scraping_sessions')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
