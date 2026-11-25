"""Small Open Library books demo: one API request, normalized nested metadata."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import dlt
import duckdb

from http_client import session

ISBN = ["9780140328721", "9780451524935", "9780061120084"]
URL = "https://openlibrary.org/api/books"


def main():
    runtime = Path("runtime")
    runtime.mkdir(exist_ok=True)
    with session() as client:
        response = client.get(URL, params={"bibkeys": ",".join(f"ISBN:{isbn}" for isbn in ISBN),
                                          "format": "json", "jscmd": "data"}, timeout=(10, 60))
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict) or not payload:
        raise ValueError("Open Library returned no book metadata")
    books = [{"bibkey": key, **record} for key, record in payload.items()]
    database = runtime / "books.duckdb"
    pipeline = dlt.pipeline(pipeline_name="open_library_pipeline", pipelines_dir=str(runtime / "pipelines"),
                            destination=dlt.destinations.duckdb(credentials=str(database)),
                            dataset_name="open_library")
    load = pipeline.run(dlt.resource(books, name="books", write_disposition="replace"))
    load.raise_on_failed_jobs()
    with duckdb.connect(str(database), read_only=True) as connection:
        tables = [row[0] for row in connection.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'open_library' AND table_name NOT LIKE '_dlt%' ORDER BY table_name"
        ).fetchall()]
        counts = {table: connection.execute(f'SELECT COUNT(*) FROM open_library."{table}"').fetchone()[0]
                  for table in tables}
        titles = connection.execute("SELECT bibkey, title FROM open_library.books ORDER BY bibkey").fetchall()
    evidence = {"observed_at_utc": datetime.now(timezone.utc).isoformat(), "source": URL,
                "requested_isbns": ISBN, "response_sha256": hashlib.sha256(response.content).hexdigest(),
                "dlt_version": dlt.__version__, "duckdb_version": duckdb.__version__,
                "table_counts": counts, "book_titles": titles}
    Path("results").mkdir(exist_ok=True)
    Path("results/open-library-observed.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(load)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
