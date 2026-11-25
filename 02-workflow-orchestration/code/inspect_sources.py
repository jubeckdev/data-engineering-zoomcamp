"""Stream course gzipped CSVs to measure homework answers without a warehouse."""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.request


class MeasuredStream(io.RawIOBase):
    def __init__(self, source):
        self.source = source
        self.bytes = 0
        self.digest = hashlib.sha256()

    def readable(self):
        return True

    def readinto(self, buffer):
        chunk = self.source.read(len(buffer))
        buffer[:len(chunk)] = chunk
        self.bytes += len(chunk)
        self.digest.update(chunk)
        return len(chunk)


def inspect(taxi, year, month):
    filename = f'{taxi}_tripdata_{year}-{month:02d}.csv'
    url = f'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/{taxi}/{filename}.gz'
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                with gzip.GzipFile(fileobj=response) as decompressed:
                    measured = MeasuredStream(decompressed)
                    with io.TextIOWrapper(io.BufferedReader(measured), newline='') as text:
                        rows = csv.reader(text)
                        header = next(rows)
                        count = sum(1 for _ in rows)
            return dict(filename=filename,taxi=taxi,year=year,month=month,
                        row_count=count,uncompressed_bytes=measured.bytes,
                        uncompressed_mib=round(measured.bytes / 1024**2,3),
                        sha256=measured.digest.hexdigest(),columns=header,source_url=url)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('homework/source-measurements.json'))
    parser.add_argument('--sample', action='store_true', help='Only inspect green January 2021')
    args = parser.parse_args()
    jobs = [('green',2021,1)] if args.sample else [
        (taxi,2020,month) for taxi in ('yellow','green') for month in range(1,13)
    ] + [('yellow',2021,3)]
    results = json.loads(args.output.read_text()) if args.output.exists() else []
    for taxi,year,month in jobs:
        if any((r['taxi'],r['year'],r['month']) == (taxi,year,month) for r in results):
            continue
        result = inspect(taxi,year,month)
        results.append(result)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(results,indent=2)+'\n')
        print(f"{result['filename']}: {result['row_count']:,} rows; {result['uncompressed_mib']} MiB", flush=True)


if __name__ == '__main__':
    main()
