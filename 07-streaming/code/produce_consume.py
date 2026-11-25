"""A deterministic finite replay through a real Kafka broker, not a simulated stream."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.request


import pandas as pd
from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from kafka.admin import KafkaAdminClient, NewTopic

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--reset", action="store_true", help="Delete and recreate ONLY the local green-trips exercise topic")
args = parser.parse_args()
topic = "green-trips"
broker = "localhost:9092"
admin = KafkaAdminClient(bootstrap_servers=broker)
if topic in admin.list_topics():
    if not args.reset:
        raise RuntimeError("Topic exists: use --reset for a deliberate clean replay")
    admin.delete_topics([topic])
    deadline = time.monotonic()+30
    while topic in admin.list_topics():
        if time.monotonic() > deadline:
            raise TimeoutError("Topic deletion did not finish")
        time.sleep(0.5)
admin.create_topics([NewTopic(topic, num_partitions=1, replication_factor=1)])
admin.close()
path = root / "runtime/green_tripdata_2025-10.parquet"
path.parent.mkdir(exist_ok=True)
if not path.exists():
    with urllib.request.urlopen("https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_2025-10.parquet", timeout=120) as response:
        path.write_bytes(response.read())
columns = ["lpep_pickup_datetime", "lpep_dropoff_datetime", "PULocationID", "DOLocationID", "passenger_count", "trip_distance", "tip_amount", "total_amount"]
df = pd.read_parquet(path, columns=columns)
if df.lpep_pickup_datetime.isna().any() or df.PULocationID.isna().any():
    raise ValueError("Null event time or key requires an explicit quarantine policy")
df = df.sort_values("lpep_pickup_datetime", kind="stable")
for col in ["lpep_pickup_datetime", "lpep_dropoff_datetime"]:
    df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
records = df.astype(object).where(pd.notna(df), None).to_dict("records")
producer = KafkaProducer(bootstrap_servers=broker, acks="all", retries=5, linger_ms=10, value_serializer=lambda value: json.dumps(value, allow_nan=False).encode())
started = time.perf_counter()
futures = [producer.send(topic, value=record, partition=0) for record in records]
print("Queued", len(futures), "records", flush=True)
producer.flush(timeout=120)
print("Flushed", flush=True)
elapsed = time.perf_counter()-started
for future in futures:
    future.get(timeout=30)
producer.close(timeout=10)
print("Producer closed", flush=True)
consumer = KafkaConsumer(bootstrap_servers=broker, group_id=None, auto_offset_reset="earliest", enable_auto_commit=False, value_deserializer=lambda data:json.loads(data))
partition = TopicPartition(topic, 0)
consumer.assign([partition])
start_offset = consumer.beginning_offsets([partition])[partition]
consumer.seek(partition, start_offset)
end = consumer.end_offsets([partition])[partition]
count = distant = 0
deadline = time.monotonic()+120
next_offset = start_offset
while next_offset < end:
    if time.monotonic() > deadline:
        raise TimeoutError("Consumer did not reach the captured ending offset")
    for messages in consumer.poll(timeout_ms=1000).values():
        for message in messages:
            next_offset = message.offset + 1
            count += 1
            distance = message.value["trip_distance"]
            distant += distance is not None and distance > 5
print("Consumed", count, flush=True)
consumer.close()
print("Consumer closed", flush=True)
assert count == len(records) == end, (count,len(records),end)
evidence = dict(verified_at=datetime.now(timezone.utc).isoformat(), source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), source_rows=len(records), produced_and_acknowledged=len(futures), consumed=count, end_offset=end, send_and_flush_seconds=elapsed, trip_distance_gt_5=distant, event_order="stable ascending pickup timestamp", partition_count=1)
(root / "homework/producer-consumer.json").write_text(json.dumps(evidence, indent=2)+"\n")
print(json.dumps(evidence, indent=2))
