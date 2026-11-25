# Module 3 — warehouse design and BigQuery

[Official homework](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/cohorts/2026/03-data-warehouse/homework.md). All six January–June 2024 yellow taxi files were independently checked with DuckDB. **BigQuery execution and byte estimates are pending**: the original GCP trial expired. Azure storage is not a replacement for these BigQuery measurements.

## Reproduce source checks

```bash
docker compose run --build --rm verify
```

[Source evidence](homework/source-results.json) includes each URL, SHA-256, byte size and row count. Observed totals: **20,332,093 rows**, **8,333 zero-fare trips**, and **262 distinct pickup location IDs**. All six files remain in ignored `runtime/` for a later GCS upload.

## BigQuery implementation

`code/warehouse.sql` defines the external Parquet table, a normal unpartitioned native table (the homework's “materialized table”, not a materialized view), and the optimized table partitioned by dropoff date and clustered on VendorID.

With an existing authorized GCP project, dataset, same-location GCS bucket and authenticated `gcloud`/`bq` tools:

```bash
python3 code/run_bigquery.py --project YOUR_PROJECT --dataset YOUR_DATASET \
  --bucket YOUR_BUCKET --location YOUR_LOCATION
# Review homework/rendered-warehouse.sql first.
# Add --execute to upload the files, replace the three homework tables,
# and save actual BigQuery dry-run output in homework/bigquery-dry-runs.json.
```

The runner does not enable billing or create a project. Executing creates billable GCS/BigQuery data and has a 10 GB query-byte limit. Credentials are provided through local SDK login, never committed. Remove the three tables and six objects when finished if storage is no longer needed.

## Answers and SQL

1. **20,332,093**, independently observed locally:

```sql
SELECT COUNT(*) FROM `PROJECT.DATASET.yellow_native`;
```

2. **Pending actual BigQuery dry runs.** Run on both `yellow_external` and `yellow_native`:

```sql
SELECT COUNT(DISTINCT PULocationID) FROM `PROJECT.DATASET.yellow_external`;
SELECT COUNT(DISTINCT PULocationID) FROM `PROJECT.DATASET.yellow_native`;
```

3. BigQuery stores data by column. Selecting both location columns reads more column data than selecting one:

```sql
SELECT PULocationID FROM `PROJECT.DATASET.yellow_native`;
SELECT PULocationID, DOLocationID FROM `PROJECT.DATASET.yellow_native`;
```

4. **8,333**, independently observed locally:

```sql
SELECT COUNT(*) FROM `PROJECT.DATASET.yellow_native` WHERE fare_amount = 0;
```

5. **Partition by dropoff date; cluster by VendorID**. See `code/warehouse.sql`.
6. **Pending actual BigQuery dry runs** on the native and optimized tables. The exclusive March 16 boundary includes the entire March 15:

```sql
SELECT DISTINCT VendorID FROM `PROJECT.DATASET.yellow_native`
WHERE tpep_dropoff_datetime >= '2024-03-01'
  AND tpep_dropoff_datetime < '2024-03-16';
SELECT DISTINCT VendorID FROM `PROJECT.DATASET.yellow_optimized`
WHERE tpep_dropoff_datetime >= '2024-03-01'
  AND tpep_dropoff_datetime < '2024-03-16';
```

7. The external table's files live in the **GCS bucket**.
8. **False**. Clustering should fit the workload and table size; it is not a universal requirement.
9. `SELECT COUNT(*)` on a native table can be answered from table metadata without scanning column data. An estimated zero-byte scan is the expected explanation; this account's actual estimate is unmeasured.

References: [external tables](https://cloud.google.com/bigquery/docs/external-tables), [partitioned tables](https://cloud.google.com/bigquery/docs/partitioned-tables), [clustered tables](https://cloud.google.com/bigquery/docs/clustered-tables).
