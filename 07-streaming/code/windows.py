"""Run each of the three event-time SQL window jobs, writing to PostgreSQL."""
import argparse
import json
from pathlib import Path

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import EnvironmentSettings, StreamTableEnvironment

parser = argparse.ArgumentParser()
parser.add_argument("job", choices=["pickup", "session", "tips"])
parser.add_argument("--continuous", action="store_true", help="Follow new messages indefinitely instead of stopping at the verified offset")
args = parser.parse_args()
env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(1)
env.enable_checkpointing(10000)
tables = StreamTableEnvironment.create(env, environment_settings=EnvironmentSettings.in_streaming_mode())
tables.get_config().set("table.local-time-zone", "UTC")
end_offset = json.loads(Path("/opt/src/homework/producer-consumer.json").read_text())["end_offset"]
bounded = "" if args.continuous else f", 'scan.bounded.mode'='specific-offsets', 'scan.bounded.specific-offsets'='partition:0,offset:{end_offset}'"
tables.execute_sql(f"""
CREATE TABLE trips (
    lpep_pickup_datetime STRING,
    lpep_dropoff_datetime STRING,
    PULocationID INT,
    DOLocationID INT,
    passenger_count DOUBLE,
    trip_distance DOUBLE,
    tip_amount DECIMAL(18,2),
    total_amount DECIMAL(18,2),
    event_timestamp AS TO_TIMESTAMP(lpep_pickup_datetime, 'yyyy-MM-dd HH:mm:ss'),
    WATERMARK FOR event_timestamp AS event_timestamp - INTERVAL '5' SECOND
) WITH (
    'connector'='kafka',
    'properties.bootstrap.servers'='redpanda:29092',
    'properties.group.id'='zoomcamp-{args.job}',
    'topic'='green-trips',
    'scan.startup.mode'='earliest-offset',
    'format'='json'
    {bounded}
)
""")
names = dict(pickup="pickup_windows", session="pickup_sessions", tips="hourly_tips")
sink = names[args.job]
metrics = "total_tip DECIMAL(18,2), num_trips BIGINT, PRIMARY KEY(window_start) NOT ENFORCED" if args.job == "tips" else "pickup_location_id INT, num_trips BIGINT, PRIMARY KEY(window_start, pickup_location_id) NOT ENFORCED"
tables.execute_sql(f"""
CREATE TABLE result_sink (
    window_start TIMESTAMP(3), window_end TIMESTAMP(3), {metrics}
) WITH (
    'connector'='jdbc', 'url'='jdbc:postgresql://postgres:5432/streaming',
    'table-name'='{sink}', 'username'='postgres', 'password'='local-only-password',
    'driver'='org.postgresql.Driver', 'sink.buffer-flush.interval'='1s'
)
""")
if args.job == "tips":
    query = """SELECT window_start, window_end, CAST(SUM(tip_amount) AS DECIMAL(18,2)), COUNT(*)
    FROM TABLE(TUMBLE(TABLE trips, DESCRIPTOR(event_timestamp), INTERVAL '1' HOUR))
    GROUP BY window_start, window_end"""
else:
    function = "SESSION(TABLE trips PARTITION BY PULocationID, DESCRIPTOR(event_timestamp), INTERVAL '5' MINUTE)" if args.job == "session" else "TUMBLE(TABLE trips, DESCRIPTOR(event_timestamp), INTERVAL '5' MINUTE)"
    query = f"SELECT window_start, window_end, PULocationID, COUNT(*) FROM TABLE({function}) GROUP BY window_start, window_end, PULocationID"
tables.execute_sql(f"INSERT INTO result_sink {query}").wait()
