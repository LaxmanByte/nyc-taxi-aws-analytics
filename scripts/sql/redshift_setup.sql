-- ================================================================
-- NYC Taxi Analytics - Redshift Serverless Setup
-- Author: Laxman Barre
-- Description: Creates main table with SORTKEY and DISTKEY
--              optimized for 10x query performance
-- ================================================================

-- ----------------------------------------------------------------
-- STEP 1: Create Schema
-- ----------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS nyc_taxi;

SET search_path TO nyc_taxi;


-- ----------------------------------------------------------------
-- STEP 2: Create Main Trips Table
-- DISTKEY on pickup_date for even data distribution
-- SORTKEY on pickup_date, pickup_hour for fast time-range queries
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nyc_taxi_trips (
    -- Trip identifiers
    vendor_id               INTEGER,

    -- Timestamps
    tpep_pickup_datetime    TIMESTAMP,
    tpep_dropoff_datetime   TIMESTAMP,
    pickup_date             DATE            DISTKEY,
    pickup_hour             INTEGER,
    pickup_day              INTEGER,
    pickup_month            INTEGER,
    pickup_year             INTEGER,

    -- Passenger & distance
    passenger_count         INTEGER,
    trip_distance           DECIMAL(10, 2),

    -- Location zones
    pu_location_id          INTEGER,
    do_location_id          INTEGER,
    rate_code_id            INTEGER,
    store_and_fwd_flag      VARCHAR(3),

    -- Fare breakdown
    fare_amount             DECIMAL(10, 2),
    extra                   DECIMAL(10, 2),
    mta_tax                 DECIMAL(10, 2),
    tip_amount              DECIMAL(10, 2),
    tolls_amount            DECIMAL(10, 2),
    improvement_surcharge   DECIMAL(10, 2),
    total_amount            DECIMAL(10, 2),
    congestion_surcharge    DECIMAL(10, 2),
    airport_fee             DECIMAL(10, 2),

    -- Payment
    payment_type            INTEGER,
    payment_type_desc       VARCHAR(20),

    -- Derived columns
    trip_duration_minutes   DECIMAL(10, 2),
    revenue_per_mile        DECIMAL(10, 2)
)
SORTKEY(pickup_date, pickup_hour);


-- ----------------------------------------------------------------
-- STEP 3: Verify Table Structure
-- ----------------------------------------------------------------
SELECT
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'nyc_taxi_trips'
ORDER BY ordinal_position;


-- ----------------------------------------------------------------
-- STEP 4: Check Row Count After Load
-- ----------------------------------------------------------------
SELECT COUNT(*) AS total_records FROM nyc_taxi_trips;


-- ----------------------------------------------------------------
-- STEP 5: Analyze Table for Query Optimizer
-- ----------------------------------------------------------------
ANALYZE nyc_taxi_trips;


-- ----------------------------------------------------------------
-- STEP 6: Run VACUUM to reclaim space after large inserts
-- ----------------------------------------------------------------
VACUUM nyc_taxi_trips;


-- ----------------------------------------------------------------
-- STEP 7: Quick sanity check queries
-- ----------------------------------------------------------------

-- Check date range of data
SELECT
    MIN(pickup_date)    AS earliest_trip,
    MAX(pickup_date)    AS latest_trip,
    COUNT(DISTINCT pickup_date) AS unique_days
FROM nyc_taxi_trips;

-- Check revenue totals
SELECT
    COUNT(*)                        AS total_trips,
    ROUND(SUM(total_amount), 2)     AS total_revenue,
    ROUND(AVG(total_amount), 2)     AS avg_fare,
    ROUND(SUM(trip_distance), 2)    AS total_miles
FROM nyc_taxi_trips;

-- Confirm SORTKEY / DISTKEY configuration
SELECT
    tablename,
    sortkey1,
    diststyle
FROM pg_table_def
WHERE tablename = 'nyc_taxi_trips'
LIMIT 1;
