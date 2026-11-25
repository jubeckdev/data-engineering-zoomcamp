# Verified progress — 25 November 2026

## Azure capstone

The Swiss Rail Observatory processes SBB station usage through private ADLS bronze/silver/gold layers, dbt/DuckDB models, Azure SQL and a portable interactive HTML dashboard.

- Terraform provisions the dedicated resources. Storage, container environment and registry are in Switzerland North; SQL uses France Central after the trial rejected Switzerland North and West Europe SQL provisioning. This is not a Swiss-only residency deployment.
- The local-to-Azure Prefect run succeeded on 24 November. Six dbt models and 12 data tests passed. Four source-contract/dashboard-escaping tests passed.
- SQL rollback testing intentionally failed after the first table swap and verified that the entire previous publication survived. A repeat publication preserved every business row and left no staging tables.
- The first managed cloud execution failed at SQL login because the contained user's SID used the managed identity principal ID. The initialization now uses its client ID, as required for this SQL user mapping; Azure RBAC continues to use the principal ID.
- Azure execution `job-swiss-rail-3evilpd` succeeded on 25 November with managed identity, without using the laptop's Azure login. It processed 5,724 station-year rows into 1,178 stations, 5,724 fact rows, 5,724 station-year reporting rows, 130 area-year rows and five common-cohort rows.
- The monthly job is configured for 06:00 UTC on the first day of each month. Manual execution is verified; a future automatic scheduled trigger has not yet been observed.
- The dashboard is a snapshot queried back from SQL and stored privately in ADLS and locally at `capstone/dashboard/index.html`. It is not a publicly hosted website. Year/area filters, station search, coverage details and empty states were checked in the browser.
- Source attribution, operators, historical coverage and metric caveats are documented. The metric is average daily boardings plus alightings, not unique passengers or annual totals. The constant cohort has 1,068 stations.

Evidence lives in `capstone/evidence/`, including local-to-cloud execution, rollback/replay checks, actual Azure execution and downloaded artifact verification. The earlier failed execution is retained in the history rather than omitted.

Published evidence normalizes workstation paths to repository-relative paths or `$HOME`. Execution results, row counts, timestamps and checksums are preserved.

## Coursework

| Component | Actual verification |
|---|---|
| Module 1 | Docker/PostgreSQL ingestion and SQL answers; 46,912 trips and 265 zones. GCP Terraform validated, not applied. |
| Module 2 | Single-month Kestra replay plus all 14 January–July 2021 tables. Every table reconciles; 570,466 green and 15,000,700 yellow rows. All 25 homework source measurements saved. |
| dlt workshops | Ten API pages produced 10,000 taxi rows, then a terminal empty page. Six tests and repeat-run reconciliation passed. Three Open Library books normalized into 18 tables. |
| Module 3 | Six January–June 2024 yellow files: 20,332,093 rows and 8,333 zero fares. BigQuery SQL and runner prepared; cloud estimates unmeasured. |
| Module 4 | All 60 fixed source files, 160,070,315 raw rows. Full production dbt build passed 45 nodes including 34 data tests. All four data answers match the listed choices. |
| Module 5 | Bruin initial, incremental and replay executions each passed 14 checks. Staging has 270,119 rows; previous-day reports preserved. |
| Module 6 | Spark 4.0.1 processed 4,181,444 rows, preserved counts across four files, passed query checks and returned HTTP 200 from the live UI. |
| Module 7 | All 49,416 Kafka messages consumed; all three Flink window outputs matched independent SQL; pickup replay preserved results. Largest session measured 82, differing from the listed 81; discrepancy disclosed. |

## Spending and access

The deployment uses Azure free-trial credit with an expiry of 22 December 2026; the subscription has not been upgraded to paid billing. Live subscription spending protection is checked separately from delayed cost reports. SQL and the Basic registry incur ongoing charges while provisioned. The job schedule and log quota are not a subscription spending cap. See `capstone/infra/azure/cost-observation.json` for the latest actual observation and its caveat. Budget notification alerts have not been configured.

The temporary operator-only SQL firewall rule is removed after independent verification. The Azure-services rule remains for the job; Entra authorization is required, but this is not private network isolation. Tokens, state, local variable files, runtime data and virtual environments remain excluded from Git. Local Docker stacks are stopped after verification; database volumes remain available.

## Remaining limitations

Original GCP deployment/flows and Module 3 BigQuery execution/scan estimates remain pending because GCP billing access is unavailable. Optional dlt dashboard/MCP and marimo interfaces were not executed.
