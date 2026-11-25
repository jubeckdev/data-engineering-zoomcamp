"""Download the homework inputs and atomically replace the local homework tables."""
import hashlib
import os
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd
from sqlalchemy import create_engine, text

SOURCES = {
    'green_tripdata_2025-11.parquet': 'https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_2025-11.parquet',
    'taxi_zone_lookup.csv': 'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/misc/taxi_zone_lookup.csv',
}

def main():
    for filename, url in SOURCES.items():
        urlretrieve(url, filename)
        print(f'{filename}: sha256={hashlib.sha256(Path(filename).read_bytes()).hexdigest()}', flush=True)
    trips = pd.read_parquet('green_tripdata_2025-11.parquet')
    zones = pd.read_csv('taxi_zone_lookup.csv')
    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.begin() as connection:
        trips.to_sql('trips', connection, if_exists='replace', index=False, chunksize=5000)
        zones.to_sql('zones', connection, if_exists='replace', index=False)
        connection.execute(text('CREATE INDEX ON trips (lpep_pickup_datetime)'))
    print(f'Loaded {len(trips)} trips and {len(zones)} zones.', flush=True)
    with engine.connect() as connection:
        for query in Path('queries.sql').read_text().split(';'):
            if query.strip():
                result = connection.execute(text(query))
                print(list(result.keys()))
                for row in result:
                    print(tuple(row))

if __name__ == '__main__':
    main()
