"""Build tested marts and versionable lake artifacts from one source snapshot."""
import json
import os
from pathlib import Path
import subprocess
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
TABLES = ["dim_station", "fct_station_usage", "mart_station_year", "mart_canton_year", "mart_common_cohort_year"]


def transform(snapshot):
    database = ROOT / "runtime/rail.duckdb"
    with duckdb.connect(str(database)) as db:
        db.execute("CREATE SCHEMA IF NOT EXISTS raw")
        db.read_json(str(snapshot)).create_view("incoming")
        db.execute("CREATE OR REPLACE TABLE raw.station_usage AS SELECT * FROM incoming")
    environment = dict(os.environ, CAPSTONE_DB_PATH=str(database), DBT_SEND_ANONYMOUS_USAGE_STATS="false")
    command = [str(Path(sys.executable).with_name("dbt")), "build", "--target", "prod", "--profiles-dir", "."]
    run = subprocess.run(command, cwd=ROOT/"dbt", env=environment, text=True, capture_output=True)
    (ROOT/"evidence/dbt-build.txt").write_text(run.stdout+run.stderr)
    run.check_returncode()
    artifacts = {}
    with duckdb.connect(str(database), read_only=True) as db:
        for table in TABLES:
            layer = "silver" if table in {"dim_station", "fct_station_usage"} else "gold"
            path = ROOT / "runtime" / layer / f"{table}.parquet"
            path.parent.mkdir(exist_ok=True)
            db.table(f"analytics.{table}").write_parquet(str(path), compression="zstd")
            artifacts[table] = dict(layer=layer, path=str(path), rows=db.table(f"analytics.{table}").count("*").fetchone()[0])
        evidence = dict(artifacts=artifacts, cohort=db.sql("SELECT * FROM analytics.mart_common_cohort_year ORDER BY observed_year").fetchall(), source_rows=db.sql("SELECT COUNT(*) FROM raw.station_usage").fetchone()[0])
    (ROOT/"evidence/transformation.json").write_text(json.dumps(evidence, default=str, indent=2)+"\n")
    return artifacts


if __name__ == "__main__":
    print(json.dumps(transform(Path(sys.argv[1])), indent=2))
