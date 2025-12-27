-- Initialize Kasparro ETL Database

-- Create database if it doesn't exist
-- (This is handled by docker-compose, but included for completeness)

-- Set timezone
SET timezone = 'UTC';

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant permissions (if needed)
-- GRANT ALL PRIVILEGES ON DATABASE kasparro_etl TO postgres;