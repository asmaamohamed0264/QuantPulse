-- QuantPulse Database Initialization Script
-- This script creates the initial database structure

-- Create database and user (run as postgres superuser)
-- CREATE DATABASE quantpulse;
-- CREATE USER quantpulse WITH ENCRYPTED PASSWORD 'quantpulse_secure_2024';
-- GRANT ALL PRIVILEGES ON DATABASE quantpulse TO quantpulse;

-- Connect to quantpulse database and run the following
\c quantpulse;

-- Enable UUID extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create some useful extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Set timezone
SET timezone = 'UTC';

-- Grant permissions on public schema
GRANT ALL ON SCHEMA public TO quantpulse;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO quantpulse;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO quantpulse;

-- Default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO quantpulse;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO quantpulse;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO quantpulse;

-- Insert default subscription plans (will be created by SQLAlchemy models)
-- These are just placeholder comments for reference:

-- QuantPulse Basic Plan
-- - Crypto trading only
-- - 5 active strategies 
-- - 100 alerts/day
-- - $29/month

-- QuantPulse Plus Plan  
-- - Crypto + Forex + Stocks
-- - 15 active strategies
-- - 500 alerts/day
-- - $79/month

-- QuantPulse Ultra Plan
-- - All markets + MT4/MT5 support
-- - Unlimited strategies
-- - Unlimited alerts
-- - $199/month

-- Add initial data after SQLAlchemy creates tables
-- (This will be handled by the application startup)

COMMIT;