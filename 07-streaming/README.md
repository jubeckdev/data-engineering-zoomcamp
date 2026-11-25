# Module 7 — Kafka-compatible streaming and PyFlink

**Verified locally on 23 November 2026.** All 49,416 October 2025 green taxi records were acknowledged by Redpanda and consumed. Three PyFlink event-time jobs wrote to PostgreSQL; every resulting window matched an independent DuckDB calculation. Replaying the pickup job preserved the same results.

[Official homework](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/cohorts/2026/07-streaming/homework.md). The ARM-compatible Flink Docker setup is adapted from the [course runtime](https://github.com/DataTalksClub/data-engineering-zoomcamp/tree/813d277/07-streaming/code), with pinned uv, loopback-only exposed ports, dedicated volumes and a smaller slot count. The homework's old `workshop/` link has moved to `code/` upstream.

## Run

Requires Docker and Python 3.13. From this directory:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
docker compose build jobmanager
docker compose up -d --wait redpanda postgres
docker compose up -d jobmanager taskmanager
docker compose exec -T redpanda rpk version
.venv/bin/python code/produce_consume.py
# Wait for http://localhost:8081 to show one registered Task Manager.
docker compose exec -T jobmanager flink run -py /opt/src/job/windows.py pickup
docker compose exec -T jobmanager flink run -py /opt/src/job/windows.py session
docker compose exec -T jobmanager flink run -py /opt/src/job/windows.py tips
.venv/bin/python code/verify_windows.py
docker compose down
```

For a deliberate clean replay, pass `--reset` to the producer. It deletes and recreates **only** this stack's `green-trips` topic. JDBC primary keys upsert matching window results; if the input scope changes, first truncate these three exercise tables to remove obsolete windows:

```bash
docker compose exec -T postgres psql -U postgres -d streaming -c \
  'TRUNCATE pickup_windows, pickup_sessions, hourly_tips;'
```

`docker compose down` preserves database and broker volumes. The local password is an exercise-only placeholder and the PostgreSQL port is bound to loopback. The streaming stack runs locally.

## Event time and reproducibility

The producer retains the eight required fields and serializes timestamps as strings. It stably orders the finite input by pickup time before replay, so the five-second watermark does not silently discard out-of-order historical events. The consumer captures the ending Kafka offset, explicitly seeks to the beginning offset, and checks that every message was consumed. Explicit offset tracking avoids the Kafka client's lazy-position initialization stall encountered during development.

Flink uses parallelism one and a five-second event-time watermark. The default verification run stops at the recorded Kafka offset, allowing final windows to close and the jobs to finish. `windows.py JOB --continuous` instead follows new records indefinitely; late events beyond the watermark can be dropped, and the final windows need newer event times to close. A finite replay verifies window logic; it does not establish production fault tolerance or a load benchmark.

The PostgreSQL sink has a primary key per window/location (or hour for tips), giving repeatable upsert results. These results are independently checked across **all windows**, not just the top answers. Session gaps use five minutes; the stored end includes the inactivity gap. Hourly money sums use decimal arithmetic.

## Observed homework answers

| Question | Observed result |
|---|---|
| 1. Redpanda version | **v25.3.9** |
| 2. Send and flush | **3.04 seconds** on this machine; nearest listed choice is 10 seconds |
| 3. `trip_distance > 5` | **8,506** |
| 4. Pickup location with largest 5-minute count | **74**, with 15 trips at 2025-10-22 08:40 |
| 5. Largest session | **82 trips**, location 74, 2025-10-08 06:46:14–08:27:40 including the closing gap |
| 6. Hour with highest total tips | **2025-10-16 18:00:00**, total **524.96** |

Question 5's choices include **81**, not the measured 82. Both Flink 2.2.0 and independent batch SQL agree on 82 for this complete, sorted replay. Input order, watermark advancement and source revisions can affect streaming results; the exact cause of the course-option difference has not been established. Do not present 81 as this run's result. The homework calls distance kilometres, but the TLC field is recorded in miles; the requested literal `> 5` comparison is used without conversion.

Useful queries:

```sql
SELECT pickup_location_id, num_trips FROM pickup_windows
ORDER BY num_trips DESC, window_start LIMIT 3;
SELECT * FROM pickup_sessions ORDER BY num_trips DESC, window_start LIMIT 3;
SELECT * FROM hourly_tips ORDER BY total_tip DESC, window_start LIMIT 3;
```

Evidence: [broker version](homework/redpanda-version.txt), [producer and consumer](homework/producer-consumer.json), [window comparison and replay](homework/windows.json), [finished Flink jobs](homework/flink-jobs.json). The source SHA-256 is included. Raw Parquet and local databases are ignored by Git.

References: [Flink Kafka bounded sources](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/connectors/table/kafka/), [Flink window functions](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/dev/table/sql/queries/window-tvf/), [TLC green-taxi data dictionary](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_green.pdf).
