"""Independent source checks; these do not measure BigQuery scan bytes."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

import duckdb

data = Path("runtime")
data.mkdir(exist_ok=True)
Path("homework").mkdir(exist_ok=True)
db = duckdb.connect()
db.execute("SET threads=2")
files = []
for month in range(1, 7):
    name = f"yellow_tripdata_2024-{month:02}.parquet"
    url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/{name}"
    path = data / name
    if not path.exists():
        tmp = path.with_suffix(".download")
        with urllib.request.urlopen(url, timeout=180) as source, tmp.open("wb") as out:
            while chunk := source.read(1024 * 1024):
                out.write(chunk)
        tmp.replace(path)
    rows, zero = db.execute("SELECT count(*), count(*) FILTER (WHERE fare_amount=0) FROM read_parquet(?)", [str(path)]).fetchone()
    files.append(dict(url=url, file=name, bytes=path.stat().st_size, sha256=hashlib.file_digest(path.open("rb"), "sha256").hexdigest(), rows=rows, zero_fares=zero))
    print(name, rows, flush=True)
paths = [str(data / f["file"]) for f in files]
distinct = db.execute("SELECT COUNT(DISTINCT PULocationID) FROM read_parquet(?)", [paths]).fetchone()[0]
result = dict(verified_at=datetime.now(timezone.utc).isoformat(), engine=f"DuckDB {duckdb.__version__}", files=files, rows=sum(f["rows"] for f in files), zero_fares=sum(f["zero_fares"] for f in files), distinct_pickup_locations=distinct, bigquery_executed=False, bigquery_estimated_bytes=None)
Path("homework/source-results.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k:v for k,v in result.items() if k != "files"}, indent=2))
