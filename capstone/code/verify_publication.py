"""Exercise rollback and replay on the capstone's dedicated analytics schema."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid

from cloud import dashboard_data, json_bytes, publish_sql, sql_connection
from transform import ROOT, TABLES


def fingerprint(data):
    # Publication IDs/times change on replay; business rows must not.
    values = {name: sorted(rows,key=lambda row:json.dumps(row,sort_keys=True,default=str)) for name,rows in data.items() if name.startswith('mart_')}
    return hashlib.sha256(json.dumps(values,sort_keys=True,default=str).encode()).hexdigest()


def verify():
    artifacts = json.loads((ROOT/'evidence/transformation.json').read_text())['artifacts']
    for name,item in artifacts.items():
        item['path']=str(ROOT/'runtime'/item['layer']/f'{name}.parquet')
    original = dashboard_data()
    before = fingerprint(original)
    original_publication = original['published_snapshot']
    bad=copy.deepcopy(artifacts)
    # Fail after staging and swapping the first table, proving the encompassing
    # transaction also restores earlier swaps, not only the failing insert.
    bad['fct_station_usage']['rows'] += 1
    try:
        publish_sql(bad,str(uuid.uuid4()),'0'*64)
    except ValueError as error:
        if 'Warehouse row count mismatch' not in str(error):
            raise
    else:
        raise AssertionError('Injected count mismatch was accepted')
    after_failure=dashboard_data()
    assert fingerprint(after_failure)==before
    assert after_failure['published_snapshot']==original_publication
    with sql_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM sys.tables WHERE schema_id=SCHEMA_ID('analytics') AND name LIKE '%_stage_%'")
            assert cursor.fetchone()[0]==0
    source_hash=original_publication[0]['source_hash']
    counts=publish_sql(artifacts,str(uuid.uuid4()),source_hash)
    assert fingerprint(dashboard_data())==before
    evidence=dict(verified_at=datetime.now(timezone.utc).isoformat(),rollback_preserved_previous_publication=True,no_staging_tables_after_rollback=True,replay_preserved_business_rows=True,warehouse_counts=counts,business_rows_sha256=before)
    (ROOT/'evidence/publication-verification.json').write_bytes(json_bytes(evidence))
    print(json.dumps(evidence,indent=2))

if __name__=='__main__':
    verify()
