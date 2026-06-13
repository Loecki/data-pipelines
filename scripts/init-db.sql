-- Creates the target warehouse database and user
-- This runs automatically when Postgres container starts for the first time

CREATE DATABASE warehouse;
CREATE USER etl_user WITH PASSWORD 'etl_password';
GRANT ALL PRIVILEGES ON DATABASE warehouse TO etl_user;

-- Connect to warehouse and create schema
\c warehouse

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO etl_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO etl_user;

-- ---- RAW layer: data as-is from source ----
CREATE TABLE IF NOT EXISTS raw_weather_observations (
    station_id      VARCHAR(10),
    timestamp       TIMESTAMP,
    temperature_c   DECIMAL(5,2),
    humidity_pct    DECIMAL(5,2),
    pressure_hpa    DECIMAL(7,2),
    wind_speed_ms   DECIMAL(5,2),
    precipitation_mm DECIMAL(5,2),
    loaded_at       TIMESTAMP DEFAULT NOW()
);

-- ---- CLEAN layer: validated + deduplicated ----
CREATE TABLE IF NOT EXISTS clean_weather_observations (
    station_id      VARCHAR(10),
    timestamp       TIMESTAMP,
    temperature_c   DECIMAL(5,2),
    humidity_pct    DECIMAL(5,2),
    pressure_hpa    DECIMAL(7,2),
    wind_speed_ms   DECIMAL(5,2),
    precipitation_mm DECIMAL(5,2),
    loaded_at       TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (station_id, timestamp)
);

-- ---- MART layer: aggregated for analysis ----
CREATE TABLE IF NOT EXISTS mart_daily_weather (
    station_id      VARCHAR(10),
    date            DATE,
    avg_temperature DECIMAL(5,2),
    min_temperature DECIMAL(5,2),
    max_temperature DECIMAL(5,2),
    avg_humidity    DECIMAL(5,2),
    total_precipitation DECIMAL(6,2),
    avg_wind_speed  DECIMAL(5,2),
    observation_count INTEGER,
    loaded_at       TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (station_id, date)
);

-- ---- Metadata: station info ----
CREATE TABLE IF NOT EXISTS dim_stations (
    station_id      VARCHAR(10) PRIMARY KEY,
    station_name    VARCHAR(100),
    latitude        DECIMAL(8,5),
    longitude       DECIMAL(8,5),
    elevation_m     DECIMAL(6,1),
    state           VARCHAR(50),
    loaded_at       TIMESTAMP DEFAULT NOW()
);
