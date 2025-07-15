-- =====================================================
-- Quick Cleanup Commands for Offers Table
-- =====================================================
-- Use these SQL commands to clean up offers with NULL discount values

-- 1. Check for problematic offers first
SELECT 
    r.name as restaurant_name,
    o.name as offer_name,
    o.discount_percentage,
    o.discount_amount,
    o.offer_type,
    o.is_active,
    COUNT(pp.id) as linked_products
FROM offers o
JOIN restaurants r ON o.restaurant_id = r.id
LEFT JOIN product_prices pp ON pp.offer_id = o.id
WHERE o.discount_percentage IS NULL AND o.discount_amount IS NULL
GROUP BY o.id, r.name, o.name, o.discount_percentage, o.discount_amount, o.offer_type, o.is_active
ORDER BY r.name, o.name;

-- 2. Count how many will be affected
SELECT 
    COUNT(*) as offers_to_delete,
    COUNT(CASE WHEN o.is_active THEN 1 END) as active_offers_to_delete,
    SUM(CASE WHEN pp.id IS NOT NULL THEN 1 ELSE 0 END) as product_prices_to_delete
FROM offers o
LEFT JOIN product_prices pp ON pp.offer_id = o.id
WHERE o.discount_percentage IS NULL AND o.discount_amount IS NULL;

-- 3. Delete product_prices linked to NULL discount offers
DELETE FROM product_prices 
WHERE offer_id IN (
    SELECT id FROM offers 
    WHERE discount_percentage IS NULL AND discount_amount IS NULL
);

-- 4. Delete the NULL discount offers themselves
DELETE FROM offers 
WHERE discount_percentage IS NULL AND discount_amount IS NULL;

-- 5. Verify cleanup was successful
SELECT COUNT(*) as remaining_null_offers
FROM offers 
WHERE discount_percentage IS NULL AND discount_amount IS NULL;

-- 6. Show final offers table status
SELECT 
    COUNT(*) as total_offers,
    COUNT(CASE WHEN is_active THEN 1 END) as active_offers,
    COUNT(CASE WHEN discount_percentage IS NOT NULL THEN 1 END) as percentage_offers,
    AVG(discount_percentage) as avg_discount_percentage
FROM offers;
