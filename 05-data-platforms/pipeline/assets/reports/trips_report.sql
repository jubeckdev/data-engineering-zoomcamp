/* @bruin
name: reports.trips_report
type: duckdb.sql
depends:
  - staging.trips
materialization:
  type: table
  strategy: time_interval
  incremental_key: trip_date
  time_granularity: date
columns:
  - name: trip_date
    type: date
    checks:
      - name: not_null
  - name: trip_count
    type: bigint
    checks:
      - name: non_negative
custom_checks:
  - name: unique_report_grain
    query: SELECT COUNT(*) FROM (SELECT trip_date, taxi_type, payment_type_name FROM reports.trips_report GROUP BY ALL HAVING COUNT(*) > 1)
    value: 0
  - name: reconciles_to_staging
    query: SELECT ABS((SELECT COALESCE(SUM(trip_count), 0) FROM reports.trips_report) - (SELECT COUNT(*) FROM staging.trips))
    value: 0
@bruin */
-- Recompute whole days because the target's grain is daily, even for a subday run.
SELECT CAST(pickup_datetime AS DATE) AS trip_date, taxi_type, payment_type_name,
       COUNT(*) AS trip_count, SUM(fare_amount) AS total_fare,
       AVG(fare_amount) AS avg_fare
FROM staging.trips
WHERE CAST(pickup_datetime AS DATE) BETWEEN '{{ start_date }}' AND '{{ end_date }}'
GROUP BY 1, 2, 3
