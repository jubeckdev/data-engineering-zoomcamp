"""Upgrade cached raw Parquet timestamp columns for predicate pushdown.

No source rows are filtered. Original source CSV checksums remain unchanged.
"""
import json
from pathlib import Path
import duckdb

root = Path(__file__).resolve().parents[1]
manifest_path = root / "homework/source-manifest.json"
manifest = json.loads(manifest_path.read_text())
db = duckdb.connect(str(root / "runtime/taxi_rides_ny.duckdb"))
db.execute("SET memory_limit='2GB'; SET threads=1; SET preserve_insertion_order=false")
for taxi in ["green", "yellow", "fhv"]:
    prefix = {"green": "lpep_", "yellow": "tpep_", "fhv": ""}[taxi]
    for path in sorted((root / "runtime" / taxi).glob("*.parquet")):
        if manifest[path.stem].get("native_timestamps"):
            continue
        expressions = ", ".join(f'CAST("{prefix}{field}" AS TIMESTAMP) AS "{prefix}{field}"' for field in ["pickup_datetime", "dropoff_datetime"])
        temp = path.with_suffix(".typed")
        db.read_parquet(str(path)).project(f"* REPLACE ({expressions})").write_parquet(str(temp), compression="zstd")
        count = db.read_parquet(str(temp)).count("*").fetchone()[0]
        assert count == manifest[path.stem]["rows"]
        temp.replace(path)
        manifest[path.stem].update(native_timestamps=True, parquet_bytes=path.stat().st_size)
        manifest_path.write_text(json.dumps(manifest, indent=2)+"\n")
        print(path.name, count, flush=True)
    pattern = str(root / "runtime" / taxi / "*.parquet").replace("'", "''")
    db.execute(f"CREATE OR REPLACE VIEW raw.{taxi}_tripdata AS SELECT * FROM read_parquet('{pattern}', union_by_name=true)")
db.close()
