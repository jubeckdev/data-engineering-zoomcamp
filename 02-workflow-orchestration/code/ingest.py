"""Load one immutable course CSV into a raw PostgreSQL month table.

Each month is replaced atomically, preserving every source record (including
identical rows). Source fields remain text in this raw layer.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import urllib.request

import psycopg2
from psycopg2 import sql


def download(url, destination):
    if destination.exists():
        return
    temporary = destination.with_suffix('.partial')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as response, temporary.open('wb') as output:
                shutil.copyfileobj(response, output)
            temporary.replace(destination)
            return
        except Exception:
            temporary.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--taxi', choices=['yellow', 'green'], required=True)
    parser.add_argument('--year', type=int, choices=range(2019, 2022), required=True)
    parser.add_argument('--month', type=int, choices=range(1, 13), required=True)
    args = parser.parse_args()
    filename = f'{args.taxi}_tripdata_{args.year}-{args.month:02d}.csv'
    table = f'{args.taxi}_{args.year}_{args.month:02d}'
    url = f'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/{args.taxi}/{filename}.gz'
    directory = Path(os.environ.get('TAXI_DATA_DIR', '/data'))
    directory.mkdir(parents=True, exist_ok=True)
    compressed = directory / (filename + '.gz')
    download(url, compressed)
    digest = hashlib.sha256()
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        extracted = Path(temporary) / filename
        with gzip.open(compressed, 'rb') as source, extracted.open('wb') as target:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
                target.write(chunk)
        size = extracted.stat().st_size
        with extracted.open(newline='') as source:
            columns = next(csv.reader(source))
        if len(columns) != len(set(columns)) or not columns:
            raise ValueError('Missing or duplicate CSV column names')
        with psycopg2.connect(os.environ['DATABASE_URL']) as connection:
            with connection.cursor() as cursor:
                cursor.execute('CREATE SCHEMA IF NOT EXISTS raw')
                cursor.execute('''CREATE TABLE IF NOT EXISTS raw.load_manifest (
                    filename TEXT PRIMARY KEY, taxi TEXT NOT NULL, year INTEGER NOT NULL,
                    month INTEGER NOT NULL, row_count BIGINT NOT NULL,
                    uncompressed_bytes BIGINT NOT NULL, sha256 TEXT NOT NULL,
                    source_url TEXT NOT NULL, loaded_at TIMESTAMPTZ NOT NULL DEFAULT now())''')
                # Serialize same-month reruns; distinct months can load independently.
                cursor.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (table,))
                cursor.execute(sql.SQL('DROP TABLE IF EXISTS raw.{}').format(sql.Identifier(table)))
                cursor.execute(sql.SQL('CREATE TABLE raw.{} ({})').format(
                    sql.Identifier(table), sql.SQL(', ').join(
                        sql.SQL('{} TEXT').format(sql.Identifier(column)) for column in columns)))
                with extracted.open() as source:
                    cursor.copy_expert(sql.SQL('COPY raw.{} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)').format(
                        sql.Identifier(table)), source)
                cursor.execute(sql.SQL('SELECT COUNT(*) FROM raw.{}').format(sql.Identifier(table)))
                count = cursor.fetchone()[0]
                cursor.execute('''INSERT INTO raw.load_manifest
                    (filename,taxi,year,month,row_count,uncompressed_bytes,sha256,source_url)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(filename) DO UPDATE SET row_count=excluded.row_count,
                    uncompressed_bytes=excluded.uncompressed_bytes,sha256=excluded.sha256,
                    source_url=excluded.source_url,loaded_at=now()''',
                    (filename,args.taxi,args.year,args.month,count,size,digest.hexdigest(),url))
        result = dict(filename=filename, row_count=count, uncompressed_bytes=size,
                      uncompressed_mib=round(size / 1024**2, 3), sha256=digest.hexdigest())
        print(json.dumps(result), flush=True)
        print('::' + json.dumps({'outputs': result}) + '::', flush=True)


if __name__ == '__main__':
    main()
