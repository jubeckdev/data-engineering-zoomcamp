-- Q1: Both pickup and drop-off bounds, so the dataset's coverage is explicit.
SELECT MIN(trip_pickup_datetime) AS earliest_pickup,
       MAX(trip_pickup_datetime) AS latest_pickup,
       MIN(trip_dropoff_datetime) AS earliest_dropoff,
       MAX(trip_dropoff_datetime) AS latest_dropoff
FROM taxi.trips;

-- Q2: The API uses text labels (Credit/Cash), not TLC numeric payment codes.
SELECT COUNT(*) AS total_trips,
       COUNT(*) FILTER (WHERE lower(trim(payment_type)) = 'credit') AS credit_trips,
       ROUND(100.0 * COUNT(*) FILTER (WHERE lower(trim(payment_type)) = 'credit')
             / NULLIF(COUNT(*), 0), 2) AS credit_percentage
FROM taxi.trips;

-- Q3: Amounts are loaded as decimals to avoid binary floating-point summation.
SELECT SUM(tip_amt) AS total_tips FROM taxi.trips;

-- Inspect all payment labels instead of assuming an encoding.
SELECT payment_type, COUNT(*) AS trips
FROM taxi.trips GROUP BY payment_type ORDER BY trips DESC, payment_type;
