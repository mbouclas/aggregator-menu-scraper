-- =====================================================
-- Scraper Database Schema Initialization
-- =====================================================
-- This script creates the complete database schema for storing
-- scraper data with time series price tracking and offer management
-- =====================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =====================================================
-- CORE TABLES
-- =====================================================

-- Scrapers (different scraper implementations)
CREATE TABLE scrapers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE, -- e.g., 'foody', 'wolt', 'efood'
    display_name VARCHAR(100) NOT NULL, -- e.g., 'Foody Scraper', 'Wolt Scraper'
    description TEXT,
    scraper_version VARCHAR(50) NOT NULL,
    scraping_method VARCHAR(50) NOT NULL, -- 'selenium', 'requests', 'api'
    requires_javascript BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Domains (delivery platforms)
CREATE TABLE domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE, -- e.g., 'foody.com.cy', 'wolt.com'
    display_name VARCHAR(100) NOT NULL, -- e.g., 'Foody Cyprus', 'Wolt'
    base_url VARCHAR(255) NOT NULL,
    scraper_id UUID REFERENCES scrapers(id), -- Which scraper handles this domain
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Restaurants (unique across all domains)
CREATE TABLE restaurants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    brand VARCHAR(255),
    slug VARCHAR(255) NOT NULL, -- e.g., 'costa-coffee', 'pasta-strada'
    address TEXT,
    phone VARCHAR(50),
    cuisine_types TEXT[], -- Array of cuisine types
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, brand) -- Ensure unique restaurant per brand
);

-- Restaurant presence on different domains (many-to-many)
CREATE TABLE restaurant_domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    domain_url TEXT NOT NULL, -- Full URL on the domain
    domain_specific_name VARCHAR(255), -- Name as it appears on this domain
    is_active BOOLEAN DEFAULT true,
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(restaurant_id, domain_id)
);

-- Categories (unique per restaurant)
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    source VARCHAR(50), -- 'heading', 'navigation', 'fallback', etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(restaurant_id, name)
);

-- Products (base product information)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    external_id VARCHAR(255), -- Original scraper ID like 'foody_prod_1'
    name VARCHAR(500) NOT NULL,
    description TEXT,
    image_url TEXT,
    options JSONB DEFAULT '[]', -- Product options/variants
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(restaurant_id, external_id)
);

-- =====================================================
-- OFFERS AND PROMOTIONS
-- =====================================================

-- Offers/Promotions
CREATE TABLE offers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    offer_type VARCHAR(50), -- 'percentage', 'fixed_amount', 'buy_x_get_y', etc.
    discount_percentage DECIMAL(5,2), -- For percentage discounts
    discount_amount DECIMAL(10,2), -- For fixed amount discounts
    currency VARCHAR(3) DEFAULT 'EUR',
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- TIME SERIES DATA
-- =====================================================

-- Product pricing history (time series data)
CREATE TABLE product_prices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price DECIMAL(10,2) NOT NULL,
    original_price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    discount_percentage DECIMAL(5,2) DEFAULT 0,
    offer_id UUID REFERENCES offers(id), -- Link to specific offer if applicable
    offer_name VARCHAR(255), -- Name of applied offer (for future iterations)
    availability BOOLEAN DEFAULT true,
    scraped_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure we don't duplicate prices for the same scrape time
    UNIQUE(product_id, scraped_at)
);

-- Restaurant metadata history (time series for restaurant info)
CREATE TABLE restaurant_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    rating DECIMAL(3,2),
    delivery_fee DECIMAL(10,2),
    minimum_order DECIMAL(10,2),
    delivery_time VARCHAR(100),
    total_products INTEGER DEFAULT 0,
    total_categories INTEGER DEFAULT 0,
    scraped_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(restaurant_id, domain_id, scraped_at)
);

-- =====================================================
-- SCRAPING METADATA
-- =====================================================

-- Scraping sessions (track each scrape run)
CREATE TABLE scraping_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scraper_id UUID NOT NULL REFERENCES scrapers(id) ON DELETE CASCADE,
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    domain_id UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    scraper_version VARCHAR(50),
    scraping_method VARCHAR(50), -- 'selenium', 'requests', etc.
    url TEXT NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds DECIMAL(10,3),
    product_count INTEGER DEFAULT 0,
    category_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'completed', -- 'completed', 'failed', 'partial'
    errors JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Product indexes
CREATE INDEX idx_products_restaurant_id ON products(restaurant_id);
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_name_trgm ON products USING gin (name gin_trgm_ops);
CREATE INDEX idx_products_external_id ON products(external_id);
CREATE INDEX idx_products_is_active ON products(is_active);

-- Product prices indexes (critical for time series queries)
CREATE INDEX idx_product_prices_product_id ON product_prices(product_id);
CREATE INDEX idx_product_prices_scraped_at ON product_prices(scraped_at);
CREATE INDEX idx_product_prices_offer_id ON product_prices(offer_id);
CREATE INDEX idx_product_prices_product_scraped ON product_prices(product_id, scraped_at);
CREATE INDEX idx_product_prices_discount ON product_prices(discount_percentage) WHERE discount_percentage > 0;
CREATE INDEX idx_product_prices_availability ON product_prices(availability);

-- Category indexes
CREATE INDEX idx_categories_restaurant_id ON categories(restaurant_id);
CREATE INDEX idx_categories_name ON categories(name);

-- Restaurant domain indexes
CREATE INDEX idx_restaurant_domains_restaurant_id ON restaurant_domains(restaurant_id);
CREATE INDEX idx_restaurant_domains_domain_id ON restaurant_domains(domain_id);
CREATE INDEX idx_restaurant_domains_is_active ON restaurant_domains(is_active);

-- Restaurant snapshot indexes
CREATE INDEX idx_restaurant_snapshots_restaurant_domain ON restaurant_snapshots(restaurant_id, domain_id);
CREATE INDEX idx_restaurant_snapshots_scraped_at ON restaurant_snapshots(scraped_at);

-- Scraping session indexes
CREATE INDEX idx_scraping_sessions_scraper_id ON scraping_sessions(scraper_id);
CREATE INDEX idx_scraping_sessions_restaurant_domain ON scraping_sessions(restaurant_id, domain_id);
CREATE INDEX idx_scraping_sessions_started_at ON scraping_sessions(started_at);
CREATE INDEX idx_scraping_sessions_status ON scraping_sessions(status);

-- Domain indexes
CREATE INDEX idx_domains_scraper_id ON domains(scraper_id);
CREATE INDEX idx_domains_name ON domains(name);

-- Scraper indexes
CREATE INDEX idx_scrapers_name ON scrapers(name);

-- Offer indexes
CREATE INDEX idx_offers_restaurant_id ON offers(restaurant_id);
CREATE INDEX idx_offers_is_active ON offers(is_active);
CREATE INDEX idx_offers_dates ON offers(start_date, end_date);

-- Restaurant indexes
CREATE INDEX idx_restaurants_name ON restaurants(name);
CREATE INDEX idx_restaurants_brand ON restaurants(brand);
CREATE INDEX idx_restaurants_slug ON restaurants(slug);

-- =====================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- =====================================================

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers to relevant tables
CREATE TRIGGER update_scrapers_updated_at BEFORE UPDATE ON scrapers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_domains_updated_at BEFORE UPDATE ON domains
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_restaurants_updated_at BEFORE UPDATE ON restaurants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_offers_updated_at BEFORE UPDATE ON offers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- USEFUL VIEWS
-- =====================================================

-- Current product prices (latest price for each product)
CREATE VIEW current_product_prices AS
SELECT DISTINCT ON (p.id) 
    p.id as product_id,
    p.external_id,
    p.name,
    p.description,
    r.name as restaurant_name,
    r.brand as restaurant_brand,
    r.slug as restaurant_slug,
    c.name as category_name,
    d.name as domain_name,
    s.name as scraper_name,
    s.display_name as scraper_display_name,
    pp.price,
    pp.original_price,
    pp.currency,
    pp.discount_percentage,
    pp.offer_name,
    pp.availability,
    pp.scraped_at,
    (pp.price < pp.original_price) as is_discounted
FROM products p
JOIN restaurants r ON p.restaurant_id = r.id
JOIN categories c ON p.category_id = c.id
JOIN product_prices pp ON p.id = pp.product_id
JOIN scraping_sessions ss ON ss.restaurant_id = r.id AND ss.started_at <= pp.scraped_at 
    AND (ss.completed_at IS NULL OR ss.completed_at >= pp.scraped_at)
JOIN domains d ON ss.domain_id = d.id
JOIN scrapers s ON ss.scraper_id = s.id
WHERE p.is_active = true
ORDER BY p.id, pp.scraped_at DESC;

-- Restaurant latest stats
CREATE VIEW restaurant_latest_stats AS
SELECT DISTINCT ON (rs.restaurant_id, rs.domain_id)
    r.id as restaurant_id,
    r.name as restaurant_name,
    r.brand,
    r.slug,
    d.name as domain_name,
    d.display_name as domain_display_name,
    s.name as scraper_name,
    s.display_name as scraper_display_name,
    rs.rating,
    rs.delivery_fee,
    rs.minimum_order,
    rs.delivery_time,
    rs.total_products,
    rs.total_categories,
    rs.scraped_at,
    rd.domain_url
FROM restaurant_snapshots rs
JOIN restaurants r ON rs.restaurant_id = r.id
JOIN domains d ON rs.domain_id = d.id
JOIN scrapers s ON d.scraper_id = s.id
JOIN restaurant_domains rd ON rd.restaurant_id = r.id AND rd.domain_id = d.id
ORDER BY rs.restaurant_id, rs.domain_id, rs.scraped_at DESC;

-- Products with price history
CREATE VIEW product_price_history AS
SELECT 
    p.id as product_id,
    p.external_id,
    p.name as product_name,
    r.name as restaurant_name,
    r.brand as restaurant_brand,
    r.slug as restaurant_slug,
    c.name as category_name,
    d.name as domain_name,
    s.name as scraper_name,
    pp.price,
    pp.original_price,
    pp.discount_percentage,
    pp.offer_name,
    pp.availability,
    pp.scraped_at,
    (pp.price < pp.original_price) as is_discounted,
    LAG(pp.price) OVER (PARTITION BY p.id ORDER BY pp.scraped_at) as previous_price,
    (pp.price - LAG(pp.price) OVER (PARTITION BY p.id ORDER BY pp.scraped_at)) as price_change
FROM products p
JOIN restaurants r ON p.restaurant_id = r.id
JOIN categories c ON p.category_id = c.id
JOIN product_prices pp ON p.id = pp.product_id
JOIN scraping_sessions ss ON ss.restaurant_id = r.id AND ss.started_at <= pp.scraped_at 
    AND (ss.completed_at IS NULL OR ss.completed_at >= pp.scraped_at)
JOIN domains d ON ss.domain_id = d.id
JOIN scrapers s ON ss.scraper_id = s.id
WHERE p.is_active = true
ORDER BY p.id, pp.scraped_at DESC;

-- Active offers view
CREATE VIEW active_offers AS
SELECT 
    o.*,
    r.name as restaurant_name,
    r.brand as restaurant_brand,
    r.slug as restaurant_slug,
    d.name as domain_name,
    s.name as scraper_name,
    s.display_name as scraper_display_name,
    COUNT(pp.id) as products_affected
FROM offers o
JOIN restaurants r ON o.restaurant_id = r.id
LEFT JOIN product_prices pp ON o.id = pp.offer_id 
    AND pp.scraped_at >= COALESCE(o.start_date, o.created_at)
    AND pp.scraped_at <= COALESCE(o.end_date, NOW())
LEFT JOIN scraping_sessions ss ON ss.restaurant_id = r.id 
    AND ss.started_at <= pp.scraped_at 
    AND (ss.completed_at IS NULL OR ss.completed_at >= pp.scraped_at)
LEFT JOIN domains d ON ss.domain_id = d.id
LEFT JOIN scrapers s ON ss.scraper_id = s.id
WHERE o.is_active = true
    AND (o.start_date IS NULL OR o.start_date <= NOW())
    AND (o.end_date IS NULL OR o.end_date >= NOW())
GROUP BY o.id, r.name, r.brand, r.slug, d.name, s.name, s.display_name
ORDER BY o.created_at DESC;

-- =====================================================
-- SAMPLE DATA INSERTION (OPTIONAL)
-- =====================================================

-- Insert initial scrapers
INSERT INTO scrapers (name, display_name, scraper_version, scraping_method, requires_javascript) VALUES
    ('foody', 'Foody Scraper', '1.0.0', 'requests', false),
    ('wolt', 'Wolt Scraper', '1.0.0', 'selenium', true)
ON CONFLICT (name) DO NOTHING;

-- Insert some initial domains
INSERT INTO domains (name, display_name, base_url, scraper_id) VALUES
    ('foody.com.cy', 'Foody Cyprus', 'https://foody.com.cy', (SELECT id FROM scrapers WHERE name = 'foody')),
    ('foody.com', 'Foody', 'https://foody.com', (SELECT id FROM scrapers WHERE name = 'foody')),
    ('wolt.com', 'Wolt', 'https://wolt.com', (SELECT id FROM scrapers WHERE name = 'wolt'))
ON CONFLICT (name) DO NOTHING;

-- =====================================================
-- USEFUL FUNCTIONS
-- =====================================================

-- Function to get price trends for a product
CREATE OR REPLACE FUNCTION get_product_price_trend(product_uuid UUID, days_back INTEGER DEFAULT 30)
RETURNS TABLE (
    scraped_at TIMESTAMP WITH TIME ZONE,
    price DECIMAL(10,2),
    original_price DECIMAL(10,2),
    discount_percentage DECIMAL(5,2),
    price_change DECIMAL(10,2),
    trend VARCHAR(10)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pp.scraped_at,
        pp.price,
        pp.original_price,
        pp.discount_percentage,
        (pp.price - LAG(pp.price) OVER (ORDER BY pp.scraped_at)) as price_change,
        CASE 
            WHEN pp.price > LAG(pp.price) OVER (ORDER BY pp.scraped_at) THEN 'UP'
            WHEN pp.price < LAG(pp.price) OVER (ORDER BY pp.scraped_at) THEN 'DOWN'
            ELSE 'STABLE'
        END as trend
    FROM product_prices pp
    WHERE pp.product_id = product_uuid
        AND pp.scraped_at >= NOW() - (days_back || ' days')::INTERVAL
    ORDER BY pp.scraped_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to find products with recent price changes
CREATE OR REPLACE FUNCTION find_recent_price_changes(days_back INTEGER DEFAULT 7)
RETURNS TABLE (
    product_name VARCHAR(500),
    restaurant_name VARCHAR(255),
    category_name VARCHAR(255),
    old_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    price_change DECIMAL(10,2),
    change_percentage DECIMAL(5,2),
    change_date TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    WITH price_changes AS (
        SELECT 
            p.name as product_name,
            r.name as restaurant_name,
            c.name as category_name,
            pp.price as new_price,
            LAG(pp.price) OVER (PARTITION BY p.id ORDER BY pp.scraped_at) as old_price,
            pp.scraped_at as change_date,
            ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY pp.scraped_at DESC) as rn
        FROM products p
        JOIN restaurants r ON p.restaurant_id = r.id
        JOIN categories c ON p.category_id = c.id
        JOIN product_prices pp ON p.id = pp.product_id
        WHERE pp.scraped_at >= NOW() - (days_back || ' days')::INTERVAL
    )
    SELECT 
        pc.product_name,
        pc.restaurant_name,
        pc.category_name,
        pc.old_price,
        pc.new_price,
        (pc.new_price - pc.old_price) as price_change,
        CASE 
            WHEN pc.old_price > 0 THEN ((pc.new_price - pc.old_price) / pc.old_price * 100)
            ELSE 0
        END as change_percentage,
        pc.change_date
    FROM price_changes pc
    WHERE pc.old_price IS NOT NULL 
        AND pc.old_price != pc.new_price
        AND pc.rn = 1
    ORDER BY ABS(pc.new_price - pc.old_price) DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- COMMENTS AND DOCUMENTATION
-- =====================================================

COMMENT ON TABLE domains IS 'Delivery platforms (foody.com.cy, wolt.com, etc.)';
COMMENT ON TABLE restaurants IS 'Unique restaurants across all platforms';
COMMENT ON TABLE restaurant_domains IS 'Many-to-many relationship between restaurants and domains';
COMMENT ON TABLE categories IS 'Product categories within each restaurant';
COMMENT ON TABLE products IS 'Base product information';
COMMENT ON TABLE offers IS 'Promotional offers and discounts';
COMMENT ON TABLE product_prices IS 'Time series data for product pricing';
COMMENT ON TABLE restaurant_snapshots IS 'Time series data for restaurant metadata';
COMMENT ON TABLE scraping_sessions IS 'Metadata about each scraping run';

COMMENT ON VIEW current_product_prices IS 'Latest price for each active product';
COMMENT ON VIEW restaurant_latest_stats IS 'Latest statistics for each restaurant on each domain';
COMMENT ON VIEW product_price_history IS 'Complete price history with change calculations';
COMMENT ON VIEW active_offers IS 'Currently active offers with product counts';

COMMENT ON FUNCTION get_product_price_trend IS 'Get price trend for a specific product over time';
COMMENT ON FUNCTION find_recent_price_changes IS 'Find products with recent price changes';

-- =====================================================
-- COMPLETION MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE 'Database schema initialization completed successfully!';
    RAISE NOTICE 'Created tables: domains, restaurants, restaurant_domains, categories, products, offers, product_prices, restaurant_snapshots, scraping_sessions';
    RAISE NOTICE 'Created views: current_product_prices, restaurant_latest_stats, product_price_history, active_offers';
    RAISE NOTICE 'Created functions: get_product_price_trend, find_recent_price_changes';
    RAISE NOTICE 'Ready to import scraper data!';
END $$;
