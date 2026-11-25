-- Render PROJECT, DATASET and BUCKET with run_bigquery.py; all are validated identifiers.
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.DATASET.yellow_external`
OPTIONS (format='PARQUET', uris=[
  'gs://BUCKET/yellow/2024/yellow_tripdata_2024-01.parquet',
  'gs://BUCKET/yellow/2024/yellow_tripdata_2024-02.parquet',
  'gs://BUCKET/yellow/2024/yellow_tripdata_2024-03.parquet',
  'gs://BUCKET/yellow/2024/yellow_tripdata_2024-04.parquet',
  'gs://BUCKET/yellow/2024/yellow_tripdata_2024-05.parquet',
  'gs://BUCKET/yellow/2024/yellow_tripdata_2024-06.parquet'
]);
CREATE OR REPLACE TABLE `PROJECT.DATASET.yellow_native` AS
SELECT * FROM `PROJECT.DATASET.yellow_external`;
CREATE OR REPLACE TABLE `PROJECT.DATASET.yellow_optimized`
PARTITION BY DATE(tpep_dropoff_datetime)
CLUSTER BY VendorID AS
SELECT * FROM `PROJECT.DATASET.yellow_native`;
