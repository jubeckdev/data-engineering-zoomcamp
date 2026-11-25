"""Run after October 1, October 2, then an October 1 rerun (see README)."""
from datetime import datetime, timezone
import json
from pathlib import Path

import duckdb

root = Path(__file__).resolve().parent
db = duckdb.connect(str(root / "runtime/taxi.duckdb"), read_only=True)
first = json.loads((root / "homework/first-run.json").read_text())
counts = {name: db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in ["ingestion.trips", "staging.trips", "reports.trips_report"]}
daily = db.execute("SELECT CAST(pickup_datetime AS DATE) AS trip_day, COUNT(*) n FROM staging.trips GROUP BY 1 ORDER BY 1").fetchall()
assert len(daily) == 2, daily
assert daily[0][1] == first["staging.trips"]
assert counts["ingestion.trips"] == counts["staging.trips"] + daily[0][1]
assert db.execute("SELECT COUNT(*)-COUNT(DISTINCT source_row_id) FROM staging.trips").fetchone()[0] == 0
assert db.execute("SELECT SUM(trip_count) FROM reports.trips_report").fetchone()[0] == counts["staging.trips"]
first_now = db.execute("SELECT * FROM reports.trips_report WHERE trip_date='2025-10-01' ORDER BY 1,2,3").fetchall()
for old, new in zip(first["report"], first_now, strict=True):
    assert [str(new[0]), *new[1:4]] == old[:4]
    for a, b in zip(old[4:], new[4:], strict=True):
        assert abs(a-b) < 0.00001
evidence = dict(verified_at=datetime.now(timezone.utc).isoformat(), bruin_version="v0.11.831", run_order=["October 1 full refresh", "October 2 incremental", "October 1 rerun"], counts=counts, daily=daily, checks={"no_duplicate_source_rows_in_staging":True, "append_history_retained":True, "first_day_report_unchanged":True, "second_day_preserved":True, "report_count_reconciles":True}, bruin_checks_per_run=14)
(root / "homework/verification.json").write_text(json.dumps(evidence, default=str, indent=2)+"\n")
print(json.dumps(evidence, default=str, indent=2))
