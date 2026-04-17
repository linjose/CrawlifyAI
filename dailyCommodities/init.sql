-- =============================================================================
-- init.sql — Database initialisation for the commodity price scraper
--
-- Run once to create the database, user, and table.
-- SQLAlchemy will also auto-create the table via create_all(), so this file
-- is provided mainly for DBA review, CI pipelines, or manual bootstrapping.
-- =============================================================================

-- 1. Create the database (run as a superuser, e.g. postgres)
--    Skip this block if the database already exists.
-- CREATE DATABASE commodities_db
--     ENCODING    'UTF8'
--     LC_COLLATE  'en_US.UTF-8'
--     LC_CTYPE    'en_US.UTF-8'
--     TEMPLATE    template0;

-- 2. Create a dedicated application user (optional but recommended)
-- CREATE USER scraper_user WITH PASSWORD 'strong_password_here';
-- GRANT CONNECT ON DATABASE commodities_db TO scraper_user;

-- =============================================================================
-- Connect to commodities_db before running the statements below.
-- \c commodities_db
-- =============================================================================

-- 3. Main prices table
CREATE TABLE IF NOT EXISTS commodity_prices (
    id             SERIAL          PRIMARY KEY,
    commodity_name VARCHAR(120)    NOT NULL,
    ticker         VARCHAR(20)     NOT NULL,
    price          NUMERIC(18, 6)  NOT NULL,
    currency       VARCHAR(10)     NOT NULL DEFAULT 'USD',
    price_date     DATE            NOT NULL,
    fetched_at     TIMESTAMP       NOT NULL DEFAULT NOW(),

    -- One row per commodity per calendar day
    CONSTRAINT uq_commodity_price_date UNIQUE (commodity_name, price_date)
);

-- 4. Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_cp_commodity_name
    ON commodity_prices (commodity_name);

CREATE INDEX IF NOT EXISTS idx_cp_price_date
    ON commodity_prices (price_date DESC);

CREATE INDEX IF NOT EXISTS idx_cp_ticker
    ON commodity_prices (ticker);

-- 5. Grant table-level privileges to the application user (optional)
-- GRANT SELECT, INSERT, UPDATE ON commodity_prices TO scraper_user;
-- GRANT USAGE, SELECT ON SEQUENCE commodity_prices_id_seq TO scraper_user;

-- =============================================================================
-- Verification query — should return 0 rows on a fresh database
-- =============================================================================
-- SELECT count(*) FROM commodity_prices;
