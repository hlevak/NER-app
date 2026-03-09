-- PostgreSQL initialization script for Label Studio NER application
-- Run as postgres superuser: psql -U postgres -f postgresql-init.sql

-- Create application user
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'label_studio_user') THEN
        CREATE ROLE label_studio_user WITH LOGIN PASSWORD 'LabelStudio2024!';
        RAISE NOTICE 'User label_studio_user created';
    ELSE
        RAISE NOTICE 'User label_studio_user already exists';
    END IF;
END
$$;

-- Create database
SELECT 'CREATE DATABASE label_studio OWNER label_studio_user ENCODING ''UTF8'' LC_COLLATE ''Russian_Russia.1251'' LC_CTYPE ''Russian_Russia.1251'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'label_studio')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE label_studio TO label_studio_user;

-- Connect to the new database and set up schema permissions
\c label_studio

GRANT ALL ON SCHEMA public TO label_studio_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO label_studio_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO label_studio_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO label_studio_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO label_studio_user;

\echo 'Database initialization complete'
\echo 'User: label_studio_user'
\echo 'Database: label_studio'
