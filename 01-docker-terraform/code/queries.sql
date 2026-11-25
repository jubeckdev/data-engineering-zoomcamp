-- Q3: Include November pickups. The upper date boundary is exclusive.
SELECT COUNT(*) AS q3_short_trips
FROM trips
WHERE lpep_pickup_datetime >= TIMESTAMP '2025-11-01'
  AND lpep_pickup_datetime < TIMESTAMP '2025-12-01'
  AND trip_distance <= 1;

-- Q4: Find the maximum valid distance for each pickup day.
SELECT CAST(lpep_pickup_datetime AS date) AS q4_pickup_day,
       MAX(trip_distance) AS longest_distance
FROM trips
WHERE trip_distance < 100
GROUP BY 1
ORDER BY longest_distance DESC, q4_pickup_day
LIMIT 1;

-- Q5: Sum charges by pickup zone on November 18.
SELECT z."Zone" AS q5_pickup_zone, SUM(t.total_amount) AS total_amount
FROM trips t JOIN zones z ON t."PULocationID" = z."LocationID"
WHERE t.lpep_pickup_datetime >= TIMESTAMP '2025-11-18'
  AND t.lpep_pickup_datetime < TIMESTAMP '2025-11-19'
GROUP BY z."Zone"
ORDER BY total_amount DESC
LIMIT 1;

-- Q6: Largest individual tip, rather than the sum of tips.
SELECT d."Zone" AS q6_dropoff_zone, MAX(t.tip_amount) AS largest_tip
FROM trips t
JOIN zones p ON t."PULocationID" = p."LocationID"
JOIN zones d ON t."DOLocationID" = d."LocationID"
WHERE p."Zone" = 'East Harlem North'
  AND t.lpep_pickup_datetime >= TIMESTAMP '2025-11-01'
  AND t.lpep_pickup_datetime < TIMESTAMP '2025-12-01'
GROUP BY d."Zone"
ORDER BY largest_tip DESC
LIMIT 1;
