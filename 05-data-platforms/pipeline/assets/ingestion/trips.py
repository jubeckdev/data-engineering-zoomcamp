"""@bruin
name: ingestion.trips
type: python
image: python:3.13
connection: duckdb-default
materialization:
  type: table
  strategy: append
columns:
  - name: source_row_id
    type: string
    checks:
      - name: not_null
  - name: pickup_datetime
    type: timestamp
    checks:
      - name: not_null
@bruin"""

import hashlib
import json
import os
from pathlib import Path
import urllib.request

import pandas as pd


def materialize():
    # Bruin intervals include their end timestamp. Use matching inclusive bounds
    # here and in SQL; explicit microsecond end times avoid day-boundary overlap.
    start = pd.Timestamp(os.environ["BRUIN_START_DATETIME"]).tz_localize(None)
    end = pd.Timestamp(os.environ["BRUIN_END_DATETIME"]).tz_localize(None)
    if end < start:
        raise ValueError("end must follow start")
    types = json.loads(os.environ["BRUIN_VARS"])["taxi_types"]
    if not types or any(t not in {"green", "yellow"} for t in types):
        raise ValueError("taxi_types must contain green and/or yellow")
    root = Path(__file__).resolve().parents[3]
    cache = root / "runtime" / "sources"
    cache.mkdir(parents=True, exist_ok=True)
    frames = []
    for month in pd.period_range(start, end, freq="M"):
        for taxi in dict.fromkeys(types):
            name = f"{taxi}_tripdata_{month}.parquet"
            path = cache / name
            if not path.exists():
                tmp = path.with_suffix(".download")
                with urllib.request.urlopen(f"https://d37ci6vzurychx.cloudfront.net/trip-data/{name}", timeout=120) as response:
                    with tmp.open("wb") as out:
                        while chunk := response.read(1024 * 1024):
                            out.write(chunk)
                tmp.replace(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            prefix = "lpep" if taxi == "green" else "tpep"
            df = pd.read_parquet(path, columns=[f"{prefix}_pickup_datetime", f"{prefix}_dropoff_datetime", "PULocationID", "DOLocationID", "fare_amount", "payment_type"])
            df = df.rename(columns={f"{prefix}_pickup_datetime": "pickup_datetime", f"{prefix}_dropoff_datetime": "dropoff_datetime", "PULocationID": "pickup_location_id", "DOLocationID": "dropoff_location_id"})
            df = df.loc[df.pickup_datetime.between(start, end)].copy()
            # File hash + physical row index identifies an extraction row without
            # pretending that a timestamp or an identical taxi trip is unique.
            df["source_row_id"] = [f"{taxi}:{digest}:{i}" for i in df.index]
            df["taxi_type"] = taxi
            df["source_file"] = name
            df["extracted_at"] = pd.Timestamp.now(tz="UTC").tz_localize(None)
            frames.append(df)
    return pd.concat(frames, ignore_index=True)
