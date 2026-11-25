# Module 6: Batch processing with PySpark

Implements the [2026 batch homework](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/cohorts/2026/06-batch/homework.md) with a local Spark session and the official November 2025 yellow taxi dataset.

From this directory:

```bash
docker compose run --build --rm spark
```

The image installs Java 21 and PySpark 4.0.1. The job uses two local worker threads, downloads inputs into ignored `runtime/`, and saves observed answers and SHA-256 checksums in `homework/results.json`. The first build downloads several hundred MB of Spark dependencies. No cloud compute is used.

The job reads the complete Parquet input, repartitions to exactly four output files, and confirms that reading them back preserves the input row count. File sizes are reported in both decimal MB and binary MiB. It counts pickups on November 15 using an inclusive lower and exclusive upper timestamp boundary, measures the longest dropoff-minus-pickup duration in hours, and joins pickup counts to zone names. All tied least-frequent observed pickup zones are returned; lookup zones with no trips are not introduced by an outer join.

Equivalent analysis SQL after registering the source as `trips`:

```sql
SELECT COUNT(*) FROM trips
WHERE tpep_pickup_datetime >= TIMESTAMP '2025-11-15'
  AND tpep_pickup_datetime < TIMESTAMP '2025-11-16';

SELECT MAX((unix_micros(CAST(tpep_dropoff_datetime AS TIMESTAMP_LTZ)) -
            unix_micros(CAST(tpep_pickup_datetime AS TIMESTAMP_LTZ))) / 3600000000.0)
FROM trips;
```

The job verifies an HTTP response from the Spark UI while the session is alive, and records the URL (normally port 4040). The UI is internal to the temporary container and stops when the job finishes. Input/output data remains on disk for reruns; only small result evidence is committed.

**Status:** successfully executed on 23 November 2026. Four-file output row counts match the complete source; the Spark UI responded with HTTP 200.

## Observed answers

1. Spark version: **4.0.1**.
2. Average output file: **26.57 MB** (25.34 MiB); nearest option **25 MB**.
3. November 15 pickups: **162,604**.
4. Longest trip: **90.65 hours**.
5. Spark UI port: **4040**, verified during the run.
6. **Governor's Island/Ellis Island/Liberty Island** is among the tied least-frequent observed zones (one trip each); all ties are recorded in the result file.

Full input rows: **4,181,444**.
