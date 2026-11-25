# Module 4 — analytics engineering

Full production build verified on 24 November 2026: **45 successful nodes, including 34 data tests**, against all 60 fixed course source files. The raw sources contain 160,070,315 rows; the deduplicated trip fact contains 112,086,662 rows. This is a local DuckDB execution, not a BigQuery deployment.

## Homework answers

| Question | Answer |
|---|---|
| 1 — `dbt run --select int_trips_unioned` | Only `int_trips_unioned`; add a leading `+` to build upstream dependencies. |
| 2 — new payment value 6 outside the accepted list | The test fails with a nonzero exit code at the default error severity. |
| 3 — monthly revenue rows | **12,184** |
| 4 — green taxi revenue leader in 2020 | **East Harlem North**, $1,815,309.55 |
| 5 — green October 2019 trips | **384,624** |
| 6 — staged FHV rows with nonnull dispatching base | **43,244,693** |

The exact queries and measured outputs are in [homework/results.json](homework/results.json). [homework/dbt-run-results.json](homework/dbt-run-results.json) records the successful production build; [homework/source-manifest.json](homework/source-manifest.json) records source URLs, hashes and row counts.

## Reproduce

Requires Python 3.13 and `uv`, a machine with 16 GiB RAM, and substantial free disk space (allow at least 35 GiB before loading/building).

```bash
cd 04-analytics-engineering
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements-lock.txt
.venv/bin/python code/load_sources.py
cd taxi_rides_ny
cp profiles.yml.example profiles.yml
../.venv/bin/dbt deps
../.venv/bin/dbt build --target prod --profiles-dir .
../.venv/bin/dbt docs generate --target prod --profiles-dir .
cd ..
.venv/bin/python code/answers.py
```

`../.venv/bin/dbt docs serve --profiles-dir .` from the dbt project opens the generated local catalog. The example profile uses relative paths and contains no credentials. The local profile, runtime data, environments and generated catalog files are ignored by Git.

## Design and adaptations

The base project comes from [DataTalksClub's 2026 course](https://github.com/DataTalksClub/data-engineering-zoomcamp/tree/813d277/04-analytics-engineering/taxi_rides_ny), snapshot `813d277`. The source files are the course's static GitHub releases, not later TLC revisions. This repository adapts that project for local execution and adds FHV staging, a reproducible loader, deterministic deduplication and execution evidence.

CSV files become compressed Parquet files with native timestamps, exposed through raw DuckDB views. Staging standardizes column names/types. The intermediate model unions green/yellow records, maps payment types and removes duplicates by vendor, pickup timestamp, pickup location and service. A surrogate key links the resulting trip grain to the fact table; zone/vendor dimensions and monthly zone revenue support analysis.

A full-data window sort exceeded the laptop's spill-space limit. The custom `monthly_table` materialization builds one service/month at a time, including out-of-year timestamps present in the source. Its batch keys are part of the duplicate key, so duplicate groups cannot straddle batches. It commits the staging batches and only replaces the published table after all batches finish. It uses deterministic tie-breaks when dropoff timestamps tie. The production profile uses one worker, an 8 GB memory limit and a 12 GB spill limit. The successful build took about 14 minutes.

`fct_trips` deliberately uses a full table refresh so historical corrections are included. The downstream aggregates preserve the upstream project's semantics. Out-of-year source records are retained rather than silently changing the assignment's input. FHV staging excludes null `dispatching_base_num` and normalizes location/timestamp names.

The one-off `code/type_cached_timestamps.py` migration converted an older all-string local cache and asserted unchanged per-file counts; fresh loads already produce typed timestamps. FHV is staged separately and is not included in the green/yellow revenue mart.
