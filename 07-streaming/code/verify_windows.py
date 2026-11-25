"""Compare every PostgreSQL window with an independent bounded SQL calculation."""
from datetime import datetime, timezone
import json
from pathlib import Path

import duckdb
import psycopg2

root = Path(__file__).resolve().parents[1]
producer = json.loads((root / "homework/producer-consumer.json").read_text())
db = duckdb.connect()
db.read_parquet(str(root / "runtime/green_tripdata_2025-10.parquet")).create_view("trips")
queries = {
    "pickup_windows": """SELECT time_bucket(INTERVAL '5 minutes', lpep_pickup_datetime) AS window_start,
        time_bucket(INTERVAL '5 minutes', lpep_pickup_datetime) + INTERVAL '5 minutes' AS window_end, PULocationID, COUNT(*)
        FROM trips GROUP BY 1, 2, 3""",
    "hourly_tips": """SELECT date_trunc('hour', lpep_pickup_datetime) AS window_start,
        date_trunc('hour', lpep_pickup_datetime) + INTERVAL '1 hour' AS window_end, SUM(CAST(tip_amount AS DECIMAL(18,2))), COUNT(*)
        FROM trips GROUP BY 1, 2""",
    "pickup_sessions": """WITH gaps AS (
        SELECT *, lpep_pickup_datetime - LAG(lpep_pickup_datetime) OVER (PARTITION BY PULocationID ORDER BY lpep_pickup_datetime) AS gap
        FROM trips
    ), numbered AS (
        SELECT *, SUM(CASE WHEN gap IS NULL OR gap > INTERVAL '5 minutes' THEN 1 ELSE 0 END)
            OVER (PARTITION BY PULocationID ORDER BY lpep_pickup_datetime) AS session_id FROM gaps
    ) SELECT MIN(lpep_pickup_datetime), MAX(lpep_pickup_datetime) + INTERVAL '5 minutes', PULocationID, COUNT(*)
      FROM numbered GROUP BY PULocationID, session_id""",
}
results = {}
with psycopg2.connect(host="localhost", port=5434, dbname="streaming", user="postgres", password="local-only-password") as connection:
    with connection.cursor() as cursor:
        for table, sql in queries.items():
            expected = set(db.execute(sql).fetchall())
            cursor.execute(f"SELECT * FROM {table}")
            actual = set(cursor.fetchall())
            if expected != actual:
                raise AssertionError(f"{table}: missing {list(expected-actual)[:3]}, unexpected {list(actual-expected)[:3]}")
            assert sum(row[-1] for row in actual) == producer["source_rows"]
            order = "total_tip DESC, window_start" if table == "hourly_tips" else "num_trips DESC, window_start, pickup_location_id"
            cursor.execute(f"SELECT * FROM {table} ORDER BY {order} LIMIT 3")
            results[table] = dict(window_rows=len(actual), source_trip_count=sum(row[-1] for row in actual), every_window_matches=True, top_three=cursor.fetchall())
evidence = dict(verified_at=datetime.now(timezone.utc).isoformat(), flink_version="2.2.0", bounded_end_offset=producer["end_offset"], watermark_delay_seconds=5, independent_engine=f"DuckDB {duckdb.__version__}", results=results)
(root / "homework/windows.json").write_text(json.dumps(evidence, default=str, indent=2)+"\n")
print(json.dumps(evidence, default=str, indent=2))
