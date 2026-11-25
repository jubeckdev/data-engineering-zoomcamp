"""Load static course releases, one month at a time, into compressed Parquet.

Raw DuckDB views avoid duplicating the full input on a laptop. Pickup/dropoff
timestamps are typed during ingestion; dbt casts the remaining fields. Downloads are atomic and
checksummed; only this loader's temporary CSV is removed after conversion.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time
import urllib.request

import duckdb

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--sample", action="store_true", help="January 2019 only; not sufficient for homework answers")
args = parser.parse_args()
runtime = ROOT / "runtime"
runtime.mkdir(exist_ok=True)
manifest_path = ROOT / "homework/source-manifest.json"
manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
db = duckdb.connect(str(runtime / "taxi_rides_ny.duckdb"))
db.execute("SET memory_limit='2GB'; SET threads=2; SET preserve_insertion_order=false")
db.execute("CREATE SCHEMA IF NOT EXISTS raw")

for taxi in ["green", "yellow", "fhv"]:
    folder = runtime / taxi
    folder.mkdir(exist_ok=True)
    years = [2019] if taxi == "fhv" or args.sample else [2019, 2020]
    for year in years:
        for month in ([1] if args.sample else range(1, 13)):
            name = f"{taxi}_tripdata_{year}-{month:02}"
            parquet = folder / f"{name}.parquet"
            if parquet.exists() and name in manifest:
                print("cached", name, flush=True)
                continue
            if shutil.disk_usage(runtime).free < 6 * 1024**3:
                raise RuntimeError("Less than 6 GiB free: stop safely before next download")
            url = f"https://github.com/DataTalksClub/nyc-tlc-data/releases/download/{taxi}/{name}.csv.gz"
            download = runtime / f"{name}.csv.gz"
            for attempt in range(4):
                try:
                    with urllib.request.urlopen(url, timeout=180) as source, download.open("wb") as out:
                        shutil.copyfileobj(source, out)
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(2 ** attempt)
            with download.open("rb") as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
            temporary = parquet.with_suffix(".partial.parquet")
            prefix = {"green": "lpep_", "yellow": "tpep_", "fhv": ""}[taxi]
            timestamps = ", ".join(f'CAST("{prefix}{field}" AS TIMESTAMP) AS "{prefix}{field}"' for field in ["pickup_datetime", "dropoff_datetime"])
            db.read_csv(str(download), header=True, all_varchar=True).project(f"* REPLACE ({timestamps})").write_parquet(str(temporary), compression="zstd")
            count = db.execute("SELECT COUNT(*) FROM read_parquet(?)", [str(temporary)]).fetchone()[0]
            temporary.replace(parquet)
            manifest[name] = dict(url=url, csv_gzip_sha256=digest, csv_gzip_bytes=download.stat().st_size, rows=count, parquet_bytes=parquet.stat().st_size, native_timestamps=True, converted_at=datetime.now(timezone.utc).isoformat())
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            download.unlink()
            print(name, count, flush=True)
    pattern = str(folder / "*.parquet").replace("'", "''")
    db.execute(f"CREATE OR REPLACE VIEW raw.{taxi}_tripdata AS SELECT * FROM read_parquet('{pattern}', union_by_name=true)")
db.close()
