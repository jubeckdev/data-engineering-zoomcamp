# Module 5 — Bruin data pipeline

This implementation follows the [2026 homework](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/cohorts/2026/05-data-platforms/homework.md) and [course tutorial](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/05-data-platforms/03-nyc-taxi-pipeline.md). It runs locally with DuckDB; Bruin Cloud deployment is outside the scope of this module.

## Run

Install [Bruin CLI v0.11.831](https://github.com/bruin-data/bruin/releases/tag/v0.11.831). From this module directory:

```bash
cp .bruin.yml.example .bruin.yml
mkdir -p runtime homework
bruin validate pipeline/pipeline.yml --config-file "$PWD/.bruin.yml"
bruin run pipeline/pipeline.yml --config-file "$PWD/.bruin.yml" \
  --start-date '2025-10-01 00:00:00' --end-date '2025-10-01 23:59:59.999999' \
  --full-refresh --workers 1
bruin run pipeline/pipeline.yml --config-file "$PWD/.bruin.yml" \
  --start-date '2025-10-02 00:00:00' --end-date '2025-10-02 23:59:59.999999' --workers 1
bruin run pipeline/pipeline.yml --config-file "$PWD/.bruin.yml" \
  --start-date '2025-10-01 00:00:00' --end-date '2025-10-01 23:59:59.999999' --workers 1
bruin lineage pipeline/assets/staging/trips.sql --full
```

The explicit configuration path is necessary inside this multi-module Git repository: automatic project discovery otherwise looks for the root `.bruin.yml`. Bruin installs isolated Python environments; requirements are pinned beside the Python asset. Runtime downloads and the local database are ignored by Git. `--full-refresh` rebuilds the module's destination tables; use it only when starting over.

## Data flow and correctness

`ingestion.trips` downloads the required monthly Parquet files, normalizes green/yellow timestamp names, and appends only the requested time interval. `ingestion.payment_lookup` seeds payment descriptions. `staging.trips` replaces that interval and removes repeated extractions using the file hash and physical row index. This preserves two distinct source rows even when their visible trip attributes match. A changed upstream file creates new identities: this exercise assumes immutable cached inputs; deliberate source revisions require a full refresh.

`reports.trips_report` aggregates by date, taxi type and payment description. It recomputes whole affected days because that is its reporting grain. The timestamp filters match Bruin's inclusive end boundaries. Quality checks cover keys, nulls, payment labels, report grain and reconciliation to staging. Negative fares are retained because the source includes corrections/refunds.

Both taxi types were executed for October 1 and 2, 2025. Each of the initial, incremental and rerun executions passed four assets and fourteen checks. The first day contained **136,720** trips. [Verification](homework/verification.json) records the final counts and first-day preservation after rerunning it; [first-run snapshot](homework/first-run.json) is the comparison baseline. Run `python verify.py` with DuckDB installed to repeat these assertions after the three runs above. It expects this exact fixture scope, not an arbitrary production database.

## Homework answers

1. `.bruin.yml` and a `pipeline/` directory containing `pipeline.yml` and `assets/` — the course template layout.
2. `time_interval` deletes and reinserts the requested interval.
3. `bruin run pipeline/pipeline.yml --var 'taxi_types=["yellow"]'` (also pass the configuration/date flags above).
4. `bruin run pipeline/assets/ingestion/trips.py --downstream` runs the changed asset and dependants. The payment lookup must already exist when starting from just this asset.
5. `name: not_null`.
6. `bruin lineage`.
7. `--full-refresh`.

Only use the variable override when intentionally selecting the source types for an extraction. Existing raw history remains available to staging on a rerun.
