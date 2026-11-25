"""Load every page of the workshop API into a reproducible DuckDB snapshot."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import dlt
import duckdb

from http_client import session

API_URL = "https://us-central1-dlthub-analytics.cloudfunctions.net/data_engineering_zoomcamp_api"
MONEY_FIELDS = {"fare_amt", "tip_amt", "tolls_amt", "total_amt", "mta_tax", "surcharge"}
DATE_FIELDS = {"trip_pickup_datetime", "trip_dropoff_datetime"}


def pages(client, manifest, max_pages=1000):
    """Page numbering starts at 1. Only an empty list terminates extraction."""
    hashes = set()
    for page in range(1, max_pages + 1):
        response = client.get(API_URL, params={"page": page}, timeout=(10, 60))
        response.raise_for_status()
        records = response.json()
        if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
            raise ValueError(f"Page {page} is not a list of record objects")
        checksum = hashlib.sha256(response.content).hexdigest()
        manifest.append({"page": page, "rows": len(records), "sha256": checksum})
        print(f"page={page} rows={len(records)}", flush=True)
        if not records:
            if page == 1:
                raise ValueError("The first page is empty; refusing to replace the snapshot")
            return
        if checksum in hashes:
            raise ValueError(f"Repeated page content at page {page}; refusing a pagination loop")
        hashes.add(checksum)
        yield records
    raise ValueError(f"Reached max_pages={max_pages} without the required empty terminal page")


def typed_record(record):
    result = {key.lower(): value for key, value in record.items()}
    for name in MONEY_FIELDS:
        if result.get(name) is not None:
            result[name] = Decimal(str(result[name]))
    for name in DATE_FIELDS:
        if result.get(name) is not None:
            result[name] = datetime.fromisoformat(result[name])
    return result


@dlt.resource(name="trips", write_disposition="replace", columns={
    **{field: {"data_type": "decimal", "precision": 18, "scale": 2} for field in MONEY_FIELDS},
    **{field: {"data_type": "timestamp", "timezone": False} for field in DATE_FIELDS},
})
def trips(client, manifest, max_pages=1000):
    for page in pages(client, manifest, max_pages):
        yield [typed_record(row) for row in page]


def query_results(database):
    result = []
    with duckdb.connect(str(database), read_only=True) as connection:
        for statement in Path("queries.sql").read_text().split(";"):
            if statement.strip():
                cursor = connection.execute(statement)
                result.append({"columns": [col[0] for col in cursor.description],
                               "rows": cursor.fetchall()})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-pages", type=int, default=1000,
                        help="safety bound; reaching this without an empty page fails")
    parser.add_argument("--query-only", action="store_true")
    args = parser.parse_args()
    if args.max_pages < 1:
        parser.error("--max-pages must be positive")
    runtime = Path("runtime")
    runtime.mkdir(exist_ok=True)
    database = runtime / "taxi_warehouse.duckdb"
    evidence_path = Path("results/taxi-observed.json")
    if args.query_only:
        print(json.dumps(query_results(database), indent=2, default=str))
        return
    previous = json.loads(evidence_path.read_text()) if evidence_path.exists() else None
    manifest = []
    pipeline = dlt.pipeline(pipeline_name="taxi_snapshot", pipelines_dir=str(runtime / "pipelines"),
                            destination=dlt.destinations.duckdb(credentials=str(database)),
                            dataset_name="taxi")
    with session() as client:
        load = pipeline.run(trips(client, manifest, args.max_pages))
    load.raise_on_failed_jobs()
    answers = query_results(database)
    loaded_rows = answers[1]["rows"][0][0]
    source_rows = sum(page["rows"] for page in manifest)
    if loaded_rows != source_rows:
        raise RuntimeError(f"Source rows {source_rows} != loaded rows {loaded_rows}")
    evidence = {"observed_at_utc": datetime.now(timezone.utc).isoformat(),
                "source": API_URL, "dlt_version": dlt.__version__, "duckdb_version": duckdb.__version__,
                "write_disposition": "replace", "page_manifest": manifest,
                "source_rows": source_rows, "loaded_rows": loaded_rows,
                "queries": answers}
    # Compare serialized values because decimals/datetimes become strings in evidence.
    comparable = json.loads(json.dumps(answers, default=str))
    if previous:
        evidence["rerun_check"] = {
            "previous_observed_at_utc": previous["observed_at_utc"],
            "same_page_checksums": previous["page_manifest"] == manifest,
            "same_loaded_row_count": previous["loaded_rows"] == loaded_rows,
            "same_query_results": previous["queries"] == comparable,
        }
    evidence_path.parent.mkdir(exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2, default=str) + "\n")
    print(load)
    print(json.dumps(evidence, indent=2, default=str))


if __name__ == "__main__":
    main()
