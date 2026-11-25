-- Verify source coverage before interpreting a total as a full year.
SELECT taxi, year, COUNT(*) AS months_loaded, SUM(row_count) AS trips
FROM raw.load_manifest
GROUP BY taxi, year ORDER BY taxi, year;

-- Q1: size of the uncompressed source file, in MiB.
SELECT filename, uncompressed_bytes, uncompressed_bytes / 1048576.0 AS mib
FROM raw.load_manifest WHERE filename = 'yellow_tripdata_2020-12.csv';

-- Q3/Q4: return an answer only when all twelve distinct months are loaded.
SELECT taxi, SUM(row_count) AS trips_2020
FROM raw.load_manifest WHERE year = 2020
GROUP BY taxi HAVING COUNT(DISTINCT month) = 12;

-- Q5: use source file month, not pickup timestamps (files can contain anomalies).
SELECT row_count FROM raw.load_manifest WHERE filename = 'yellow_tripdata_2021-03.csv';
