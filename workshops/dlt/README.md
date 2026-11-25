# dlt workshop: public APIs to DuckDB

This implements the [2026 workshop](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/cohorts/2026/workshops/dlt/README.md) and its [custom taxi API homework](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/cohorts/2026/workshops/dlt/dlt_homework.md). It includes the Open Library books demo and a separate paginated taxi pipeline. Both execute locally; no cloud account or API key is required.

## Run

From this folder, with Docker Desktop running:

```bash
docker compose build
docker compose run --rm pipeline python -m unittest -v test_pagination
docker compose run --rm pipeline python taxi_pipeline.py
docker compose run --rm pipeline python taxi_pipeline.py --query-only
# Re-run the full snapshot to verify it does not append duplicate loads:
docker compose run --rm pipeline python taxi_pipeline.py
# Separate Open Library demo:
docker compose run --rm pipeline python open_library_pipeline.py
```

The initial build downloads the pinned Python dependencies. Each run creates a temporary container and keeps database/state files under ignored `runtime/`. Small evidence JSON files are written to `results/`. The services use no published ports and do not leave a database server running. Run commands sequentially because DuckDB permits only one writer process.

To use a local Python 3.13 virtual environment instead:

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python taxi_pipeline.py
```

## Extraction, normalization, loading

`taxi_pipeline.py` requests `page=1`, then 2, 3 and so on from the workshop API. A short nonempty page does **not** stop extraction: only the documented empty page terminates it. HTTP errors are raised, transient responses are retried, repeated pages are rejected, and an upper safety bound fails instead of pretending a partial extract is complete. An empty first page is rejected to avoid replacing a previous dataset with nothing.

The API provides no reliable unique trip ID, so this exercise uses a **full snapshot with `replace`**, preserving duplicate records if they exist in the source. It does not invent a primary key that could incorrectly collapse legitimate trips. Re-running replaces the snapshot instead of appending another copy. This is intentionally not an incremental-loading pipeline; a production incremental design would need an upstream cursor, stable record key, and late-arrival policy.

Before dlt normalizes the records, money is converted to `Decimal` and date strings to datetimes. Currency columns use `DECIMAL(18,2)` and trip timestamps preserve the source's naive local values. dlt creates a DuckDB schema named `taxi`, the `trips` table, and its own load/state metadata tables. Optional source fields with only null values may not acquire a schema column until a non-null value arrives.

`open_library_pipeline.py` makes a single batch request for three ISBNs using the public Books API. It loads a separate `open_library` dataset and allows dlt to normalize nested lists such as authors and publishers into child tables. It does not download book text or cover images. Evidence records the actual tables and row counts returned by this live API.

## Homework investigation

All answer SQL is in [queries.sql](queries.sql). It reports:

1. Minimum and maximum pickup **and** drop-off timestamps, making date-boundary differences visible.
2. Credit-card trips divided by all trips. The source uses the text label `Credit`, so a numeric `payment_type = 1` filter would be wrong here. The final query lists every observed payment label as a cross-check.
3. Sum of `tip_amt` using exact decimal arithmetic.

The pipeline runs the queries directly through DuckDB. This is the verified inspection path; the optional dlt dashboard/MCP and bonus marimo visualization were not run. The original workshop's [dashboard guide](https://dlthub.com/docs/general-usage/dashboard) and [MCP setup](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/cohorts/2026/workshops/dlt/README.md) explain those additional interfaces.

## Evidence and checks

Execution evidence will be saved as `results/taxi-observed.json` and `results/open-library-observed.json` when the corresponding commands succeed. Taxi evidence includes UTC observation time, dependency versions, a checksum and row count for every API page (including the final empty page), source/load count reconciliation and query output. On subsequent runs it also compares page checksums, row count, and query results with the preceding evidence file.

The six unit checks cover short-page continuation, terminal empty pages, repeated-page loops, malformed response envelopes, page-bound exhaustion, and decimal conversion. A real two-run comparison establishes snapshot rerun behavior; unit checks alone do not establish upstream dataset completeness or database load success.

## Sources and attribution

- Taxi homework specification and custom API: [DataTalksClub / dltHub 2026 workshop](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/cohorts/2026/workshops/dlt/dlt_homework.md). The API is a workshop-hosted NYC taxi extract; do not assume it is the full TLC monthly dataset. Raw records and databases are not committed.
- Book metadata: [Open Library Books API](https://openlibrary.org/dev/docs/api/books). See [Open Library's licensing statement](https://openlibrary.org/developers/licensing) and [data-use FAQ](https://openlibrary.org/help/faq/using). The project uses catalog metadata only, and makes no claim to rights in book text or artwork.
- Pipeline behavior: [dlt resource/write-disposition documentation](https://dlthub.com/docs/general-usage/resource).

Course instructions and upstream datasets are attributed to their respective authors above.

## Observed homework results (23 November 2026)

The complete API snapshot contains **10,000 trips** over ten nonempty pages, followed by an empty eleventh page. Pickup timestamps cover **1–30 June 2009**; the latest drop-off is **1 July 2009 at 00:03**. **26.66%** of trips use credit cards (2,666 / 10,000), and total tips are **$6,063.41**. Six pagination/currency tests passed. See the result JSON for exact timestamps, checksums and rerun evidence.

The final rerun matched page checksums, loaded count, and every query result. Payment categories with tied counts use an alphabetical tie-breaker for deterministic comparison. The Open Library run loaded three books and normalized nested metadata into 18 tables (including the main books table).
