/* @bruin
name: staging.trips
type: duckdb.sql
depends:
  - ingestion.trips
  - ingestion.payment_lookup
materialization:
  type: table
  strategy: time_interval
  incremental_key: pickup_datetime
  time_granularity: timestamp
columns:
  - name: source_row_id
    type: string
    primary_key: true
    checks:
      - name: unique
      - name: not_null
  - name: pickup_datetime
    type: timestamp
    checks:
      - name: not_null
  - name: payment_type_name
    type: string
    checks:
      - name: not_null
custom_checks:
  - name: nonempty
    query: SELECT CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END FROM staging.trips
    value: 1
@bruin */
SELECT t.*, COALESCE(p.payment_type_name, 'unknown') AS payment_type_name
FROM ingestion.trips t
LEFT JOIN ingestion.payment_lookup p ON t.payment_type = p.payment_type_id
WHERE pickup_datetime BETWEEN '{{ start_datetime }}' AND '{{ end_datetime }}'
QUALIFY ROW_NUMBER() OVER (PARTITION BY source_row_id ORDER BY extracted_at DESC) = 1
