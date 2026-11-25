# Module 2: Workflow orchestration with Kestra

This module implements a local version of the [2026 homework](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/cohorts/2026/02-workflow-orchestration/homework.md). It uses the course's fixed CSV releases and Kestra version family, with PostgreSQL as a local destination. The original GCP deployment remains separate and unexecuted.

## Run the local workflow

From this directory with Docker Desktop running:

```bash
docker compose up --build -d
```

The first build downloads a large Kestra image and installs the Python PostgreSQL driver. Allow several minutes and several GB of disk. Kestra is at <http://localhost:8082>. The development-only login is `admin@local.test` / `LocalZoomcamp123!`. The UI is bound to localhost, PostgreSQL has no host port, and the container does not mount the Docker socket. This is a trusted-code local exercise, not an internet-facing deployment.

Once the UI responds:

```bash
python3 code/kestra.py import
python3 code/kestra.py run --taxi green --year 2021 --month 01 \
  --output homework/green-2021-01-execution.json
```

`taxi_month` renders its filename from inputs, downloads and decompresses the source, loads a raw per-month PostgreSQL table, and records row count, uncompressed size, checksum and source URL in `raw.load_manifest`. The output JSON also appears in the execution log.

All source columns remain text in the raw landing tables. Typed analytics models belong in later modules. Exact duplicate source rows are retained, so homework counts describe the CSV rather than a deduplicated approximation. The loader replaces one month's table in a database transaction; errors roll back the replacement. A transaction-scoped lock serializes concurrent runs for the same month. Other months are independent.

Inspect the loaded data and run homework SQL:

```bash
docker compose exec -T postgres psql -U kestra -d kestra < code/queries.sql
docker compose exec -T postgres psql -U kestra -d kestra \
  -c 'SELECT COUNT(*) FROM raw.green_2021_01;'
```

Run the same flow again to check that the count and checksum remain the same. Only the manifest's `loaded_at` timestamp changes.

## Backfill and scheduling

The `backfill_2021` flow uses `ForEach` with sequential `Subflow` tasks to run both colors for January through July 2021:

```bash
python3 code/kestra.py run --flow backfill_2021 --timeout 14400 \
  --output homework/backfill-2021-execution.json
```

This downloads and stores all 14 months and can consume substantial time and disk; run it only after the single-month check. Per-month cached compressed files avoid repeated downloads. Removing a cached file from the module's Docker data volume forces a fresh download if investigating a changed upstream release.

The separate `schedule_example` demonstrates `timezone: America/New_York` on a monthly Schedule trigger. It is disabled by default and only logs a message; it does not silently fetch future data. The fixed 2021 backfill is the actual homework ingestion path.

## Measure homework inputs without a large database

The homework also asks about all twelve 2020 source files for each color. The helper below streams and parses each gzipped CSV without storing its rows on disk. It writes a small JSON manifest after each successful file and resumes by skipping already measured files:

```bash
python3 code/inspect_sources.py --output homework/source-measurements.json
```

For a fresh independent measurement, choose a new output path. The manifest records the URL, columns, SHA-256 of uncompressed bytes, exact file size, and parsed CSV row count. This verifies source-file questions, but is not evidence that a Kestra backfill or cloud load ran.

## Homework answers

Numerical answers below were calculated from the recorded source measurements.

1. Yellow December 2020 uncompressed size: **134,481,400 bytes (128.25 MiB; approximately 134.5 MB)**.
2. Rendered filename: **`green_tripdata_2020-04.csv`**. Input substitution in `taxi_month.yaml` gives this value.
3. Yellow 2020 total: **24,648,499 rows**, across twelve files.
4. Green 2020 total: **1,734,051 rows**, across twelve files.
5. Yellow March 2021 count: **1,925,152 rows**.
6. Set **`timezone: America/New_York`** in the Schedule trigger. The named timezone accounts for daylight-saving changes; a fixed UTC offset does not.

Queries are in [`code/queries.sql`](code/queries.sql). The annual query deliberately returns a result only when all twelve distinct months are loaded; counting an incomplete backfill would produce a misleading answer.

## Original GCP path

The [course's scheduled GCP flow](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/02-workflow-orchestration/flows/09_gcp_taxi_scheduled.yaml) uploads CSVs to GCS and creates/merges BigQuery tables. It requires a funded/authenticated GCP project, bucket and dataset, with the matching Kestra configuration. The GCP trial expired before deployment, so this flow remains unverified. Azure capstone infrastructure is maintained separately.

## Stop and preserve the work

```bash
docker compose down
```

Named volumes preserve Kestra executions and loaded tables. To deliberately delete only this module's local volumes, use `docker compose down -v` after saving any needed evidence.

## Verification status

On 23 November 2026, the green January 2021 Kestra flow and its rerun both succeeded. The raw table contains **76,518 rows** and its source SHA-256 is `06a5ef09a6c3cf9fab195c369c7f67cd5cae600c264279e147f6d2a7abc76597`. Execution records are in `homework/green-2021-01-execution.json` and `homework/green-2021-01-rerun.json`. The 25-file source manifest covers all 2020 months for both colors plus yellow March 2021. On 24 November 2026, the full January–July 2021 backfill succeeded: **14 tables**, **570,466 green trips** and **15,000,700 yellow trips**. Every physical PostgreSQL table count matched its load manifest. See `homework/backfill-2021-execution.json`, `backfill-2021-manifest.json` and `backfill-2021-verification.json`. The original GCP flow remains unexecuted; the local workflow is the documented adaptation.
