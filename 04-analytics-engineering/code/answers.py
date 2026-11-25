import json
from datetime import datetime, timezone
from pathlib import Path
import duckdb

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "homework/source-manifest.json").read_text())
expected = {f"{taxi}_tripdata_{year}-{month:02}" for taxi in ['green', 'yellow', 'fhv'] for year in ([2019] if taxi == 'fhv' else [2019, 2020]) for month in range(1, 13)}
if set(manifest) != expected:
    raise RuntimeError("All 60 fixed source files are required before producing homework answers")
db = duckdb.connect(str(root / "runtime/taxi_rides_ny.duckdb"), read_only=True)
queries = {
    "q3_monthly_revenue_rows": "SELECT COUNT(*) FROM prod.fct_monthly_zone_revenue",
    "q4_green_2020_top_zone": "SELECT pickup_zone, SUM(revenue_monthly_total_amount) revenue FROM prod.fct_monthly_zone_revenue WHERE service_type='Green' AND revenue_month >= '2020-01-01' AND revenue_month < '2021-01-01' GROUP BY 1 ORDER BY 2 DESC LIMIT 1",
    "q5_green_october_2019_trips": "SELECT SUM(total_monthly_trips) FROM prod.fct_monthly_zone_revenue WHERE service_type='Green' AND revenue_month='2019-10-01'",
    "q6_fhv_staged_rows": "SELECT COUNT(*) FROM prod.stg_fhv_tripdata",
    "fact_rows": "SELECT COUNT(*) FROM prod.fct_trips",
}
results = {name: dict(sql=sql, rows=db.execute(sql).fetchall()) for name,sql in queries.items()}
evidence = dict(verified_at=datetime.now(timezone.utc).isoformat(), target='prod', source_files=len(manifest), duckdb_version=duckdb.__version__, results=results)
(root / "homework/results.json").write_text(json.dumps(evidence, indent=2, default=str) + "\n")
print(json.dumps(evidence, indent=2, default=str))
