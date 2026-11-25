"""Explicit GCP runner. Requires an existing authorized dataset/bucket and gcloud/bq login."""
import argparse
import json
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--project", required=True)
parser.add_argument("--dataset", required=True)
parser.add_argument("--bucket", required=True)
parser.add_argument("--location", required=True)
parser.add_argument("--execute", action="store_true", help="Upload six files and replace only the three named homework tables")
args = parser.parse_args()
for value, pattern in [(args.project, r"[a-z][a-z0-9-]{4,61}[a-z0-9]"), (args.dataset, r"[A-Za-z_][A-Za-z0-9_]*"), (args.bucket, r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]"), (args.location, r"[A-Za-z0-9-]+")]:
    if not re.fullmatch(pattern, value):
        parser.error("invalid cloud identifier")
root = Path(__file__).resolve().parents[1]
sql = (root / "code/warehouse.sql").read_text().replace("PROJECT", args.project).replace("DATASET", args.dataset).replace("BUCKET", args.bucket)
(root / "homework").mkdir(exist_ok=True)
(root / "homework/rendered-warehouse.sql").write_text(sql)
if not args.execute:
    print("Rendered SQL only. Use --execute after reviewing the existing GCP destination and costs.")
    raise SystemExit(0)
paths = [root / f"runtime/yellow_tripdata_2024-{month:02}.parquet" for month in range(1, 7)]
if not all(p.is_file() for p in paths):
    parser.error("run the source verifier first; all six inputs are required")
subprocess.run(["gcloud", "storage", "cp", *map(str, paths), f"gs://{args.bucket}/yellow/2024/"], check=True)
base = ["bq", f"--project_id={args.project}", f"--location={args.location}", "--format=json", "query", "--use_legacy_sql=false", "--use_cache=false"]
subprocess.run(base + ["--maximum_bytes_billed=10000000000", sql], check=True)
prefix = f"{args.project}.{args.dataset}"
queries = {
    "q1_count": f"SELECT COUNT(*) AS rows FROM `{prefix}.yellow_native`",
    "q2_external": f"SELECT COUNT(DISTINCT PULocationID) FROM `{prefix}.yellow_external`",
    "q2_native": f"SELECT COUNT(DISTINCT PULocationID) FROM `{prefix}.yellow_native`",
    "q3_one_column": f"SELECT PULocationID FROM `{prefix}.yellow_native`",
    "q3_two_columns": f"SELECT PULocationID, DOLocationID FROM `{prefix}.yellow_native`",
    "q4_zero_fares": f"SELECT COUNT(*) FROM `{prefix}.yellow_native` WHERE fare_amount=0",
    "q6_native": f"SELECT DISTINCT VendorID FROM `{prefix}.yellow_native` WHERE tpep_dropoff_datetime >= '2024-03-01' AND tpep_dropoff_datetime < '2024-03-16'",
    "q6_partitioned": f"SELECT DISTINCT VendorID FROM `{prefix}.yellow_optimized` WHERE tpep_dropoff_datetime >= '2024-03-01' AND tpep_dropoff_datetime < '2024-03-16'",
}
evidence = {}
for name, query in queries.items():
    run = subprocess.run(base + ["--dry_run", query], check=True, text=True, capture_output=True)
    evidence[name] = dict(query=query, dry_run_stdout=run.stdout, dry_run_stderr=run.stderr)
(root / "homework/bigquery-dry-runs.json").write_text(json.dumps(evidence, indent=2) + "\n")
