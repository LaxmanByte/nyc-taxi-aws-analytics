-- ================================================================
-- NYC Taxi Analytics - Analytical SQL Views
-- Author: Laxman Barre
-- Description: 5 analytical views for Grafana dashboards
--              Runs on Redshift Serverless
-- ================================================================

-- ----------------------------------------------------------------
-- VIEW 1: Daily Revenue Trends
-- Used for: Line graph in Grafana - Revenue over time
-- ----------------------------------------------------------------
CREATE OR REPLACE VIEW vw_daily_revenue AS
SELECT
    pickup_date,
    COUNT(*)                              AS total_trips,
    ROUND(SUM(total_amount), 2)           AS total_revenue,
    ROUND(AVG(total_amount), 2)           AS avg_fare_per_trip,
    ROUND(SUM(tip_amount), 2)             AS total_tips,
    ROUND(AVG(trip_distance), 2)          AS avg_trip_distance
FROM nyc_taxi_trips
GROUP BY pickup_date
ORDER BY pickup_date;


-- ----------------------------------------------------------------
-- VIEW 2: Peak Hour Analysis
-- Used for: Bar chart in Grafana - Busiest hours of the day
-- ----------------------------------------------------------------
CREATE OR REPLACE VIEW vw_peak_hour_analysis AS
SELECT
    pickup_hour,
    COUNT(*)                              AS total_trips,
    ROUND(AVG(total_amount), 2)           AS avg_fare,
    ROUND(AVG(trip_distance), 2)          AS avg_distance,
    ROUND(AVG(trip_duration_minutes), 2)  AS avg_duration_minutes,
    ROUND(SUM(total_amount), 2)           AS total_revenue
FROM nyc_taxi_trips
GROUP BY pickup_hour
ORDER BY pickup_hour;


-- ----------------------------------------------------------------
-- VIEW 3: Payment Type Distribution
-- Used for: Pie chart in Grafana - Cash vs Credit Card
-- ----------------------------------------------------------------
CREATE OR REPLACE VIEW vw_payment_distribution AS
SELECT
    payment_type_desc,
    COUNT(*)                                        AS total_trips,
    ROUND(SUM(total_amount), 2)                     AS total_revenue,
    ROUND(AVG(total_amount), 2)                     AS avg_fare,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage_share
FROM nyc_taxi_trips
GROUP BY payment_type_desc
ORDER BY total_trips DESC;


-- ----------------------------------------------------------------
-- VIEW 4: Top Routes by Fare Amount
-- Used for: Table in Grafana - Highest earning pickup/dropoff zones
-- ----------------------------------------------------------------
CREATE OR REPLACE VIEW vw_top_routes AS
SELECT
    PULocationID                          AS pickup_zone,
    DOLocationID                          AS dropoff_zone,
    COUNT(*)                              AS total_trips,
    ROUND(AVG(total_amount), 2)           AS avg_fare,
    ROUND(SUM(total_amount), 2)           AS total_revenue,
    ROUND(AVG(trip_distance), 2)          AS avg_distance_miles
FROM nyc_taxi_trips
WHERE PULocationID IS NOT NULL
  AND DOLocationID IS NOT NULL
GROUP BY PULocationID, DOLocationID
HAVING COUNT(*) > 100
ORDER BY total_revenue DESC
LIMIT 50;


-- ----------------------------------------------------------------
-- VIEW 5: Trip Duration Analysis
-- Used for: Histogram in Grafana - Distribution of trip lengths
-- ----------------------------------------------------------------
CREATE OR REPLACE VIEW vw_trip_duration_analysis AS
SELECT
    CASE
        WHEN trip_duration_minutes BETWEEN 0  AND 5  THEN '0-5 min'
        WHEN trip_duration_minutes BETWEEN 6  AND 15 THEN '6-15 min'
        WHEN trip_duration_minutes BETWEEN 16 AND 30 THEN '16-30 min'
        WHEN trip_duration_minutes BETWEEN 31 AND 60 THEN '31-60 min'
        ELSE '60+ min'
    END                                   AS duration_bucket,
    COUNT(*)                              AS total_trips,
    ROUND(AVG(total_amount), 2)           AS avg_fare,
    ROUND(AVG(trip_distance), 2)          AS avg_distance,
    ROUND(SUM(total_amount), 2)           AS total_revenue
FROM nyc_taxi_trips
GROUP BY 1
ORDER BY
    CASE
        WHEN duration_bucket = '0-5 min'   THEN 1
        WHEN duration_bucket = '6-15 min'  THEN 2
        WHEN duration_bucket = '16-30 min' THEN 3
        WHEN duration_bucket = '31-60 min' THEN 4
        ELSE 5
    END;


-- ----------------------------------------------------------------
-- BONUS: Weekly Revenue Summary
-- ----------------------------------------------------------------
CREATE OR REPLACE VIEW vw_weekly_revenue AS
SELECT
    DATE_TRUNC('week', pickup_date)       AS week_start,
    COUNT(*)                              AS total_trips,
    ROUND(SUM(total_amount), 2)           AS total_revenue,
    ROUND(AVG(total_amount), 2)           AS avg_fare,
    ROUND(SUM(tip_amount), 2)             AS total_tips
FROM nyc_taxi_trips
GROUP BY DATE_TRUNC('week', pickup_date)
ORDER BY week_start;
