"""Execute the 2026 batch homework on actual TLC data using local Spark."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import urlretrieve, urlopen
from pyspark.sql import SparkSession, functions as F


def main():
    data = Path('runtime')
    data.mkdir(exist_ok=True)
    sources = {
        'yellow_tripdata_2025-11.parquet': 'https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-11.parquet',
        'taxi_zone_lookup.csv': 'https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv',
    }
    checksums = {}
    for name, url in sources.items():
        path = data / name
        if not path.exists():
            temp = path.with_suffix('.download')
            urlretrieve(url, temp)
            temp.replace(path)
        checksums[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    spark = (SparkSession.builder.master('local[2]').appName('zoomcamp-module6')
             .config('spark.driver.memory', '2g').config('spark.sql.session.timeZone', 'UTC')
             .config('spark.sql.shuffle.partitions', '4').getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    try:
        trips = spark.read.parquet(str(data / 'yellow_tripdata_2025-11.parquet'))
        trips.createOrReplaceTempView('trips')
        row_count = trips.count()
        destination = data / 'four_partitions'
        trips.repartition(4).write.mode('overwrite').parquet(str(destination))
        parts = sorted(destination.glob('*.parquet'))
        assert len(parts) == 4, f'Expected four output files, got {len(parts)}'
        assert spark.read.parquet(str(destination)).count() == row_count
        count = spark.sql("""SELECT COUNT(*) AS trips FROM trips
            WHERE tpep_pickup_datetime >= TIMESTAMP '2025-11-15'
              AND tpep_pickup_datetime < TIMESTAMP '2025-11-16'""").first()['trips']
        longest = spark.sql("""SELECT MAX((unix_micros(CAST(tpep_dropoff_datetime AS TIMESTAMP_LTZ)) -
            unix_micros(CAST(tpep_pickup_datetime AS TIMESTAMP_LTZ))) / 3600000000.0) AS hours FROM trips""").first()['hours']
        zones = spark.read.option('header', True).option('inferSchema', True).csv(str(data / 'taxi_zone_lookup.csv'))
        totals = trips.groupBy('PULocationID').count()
        ranked = totals.join(zones, totals.PULocationID == zones.LocationID).select('LocationID', 'Zone', 'count')
        minimum = ranked.agg(F.min('count')).first()[0]
        least = [row.asDict() for row in ranked.filter(F.col('count') == minimum).orderBy('LocationID').collect()]
        with urlopen(spark.sparkContext.uiWebUrl, timeout=10) as response:
            ui_status = response.status
        evidence = {'observed_at_utc': datetime.now(timezone.utc).isoformat(), 'spark_version': spark.version,
                    'input_rows': row_count, 'sources': sources, 'sha256': checksums,
                    'parquet_file_bytes': [p.stat().st_size for p in parts],
                    'average_mb': sum(p.stat().st_size for p in parts)/len(parts)/1000000,
                    'average_mib': sum(p.stat().st_size for p in parts)/len(parts)/1048576,
                    'november_15_trips': count, 'longest_trip_hours': str(longest),
                    'spark_ui': spark.sparkContext.uiWebUrl, 'spark_ui_http_status': ui_status,
                    'least_frequent_observed_pickup_zones': least}
        Path('homework').mkdir(exist_ok=True)
        Path('homework/results.json').write_text(json.dumps(evidence, indent=2) + '\n')
        print(json.dumps(evidence, indent=2), flush=True)
    finally:
        spark.stop()


if __name__ == '__main__':
    main()
