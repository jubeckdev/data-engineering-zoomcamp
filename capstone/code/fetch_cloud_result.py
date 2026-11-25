"""Verify a completed Azure execution and retrieve its private dashboard artifacts."""
from datetime import datetime, timezone
import hashlib
import json
import subprocess
from cloud import lake, dashboard_data, json_bytes, sql_connection
from transform import ROOT
from verify_publication import fingerprint


def fetch():
    expected = json.loads((ROOT/'evidence/cloud-execution-start.json').read_text())['name']
    runs = json.loads(subprocess.check_output(['az','containerapp','job','execution','list','--name','job-swiss-rail','--resource-group','rg-zoomcamp-portfolio-dev','-o','json']))
    (ROOT/'evidence/cloud-executions.json').write_bytes(json_bytes(runs))
    execution = next(run for run in runs if run['name']==expected)
    if execution['properties']['status'] != 'Succeeded':
        raise RuntimeError(f"Azure execution is {execution['properties']['status']}")
    client = lake().get_container_client('gold')
    dashboard = json.loads(client.download_blob('swiss-rail/dashboard/current.json').readall())
    run_id = dashboard['published_snapshot'][0]['run_id']
    prefix = f'swiss-rail/runs/{run_id}/'
    evidence = json.loads(client.download_blob(prefix+'verification.json').readall())
    assert evidence['status']=='SUCCESS' and evidence['run_id']==run_id
    assert evidence['destination']=='ADLS Gen2 and Azure SQL'
    started = datetime.fromisoformat(execution['properties']['startTime'].replace('Z','+00:00'))
    assert datetime.fromisoformat(evidence['source']['fetched_at']) >= started
    assert dashboard['published_snapshot'][0]['source_hash']==evidence['source']['sha256']
    # Compare the same JSON representation: SQL returns Decimal objects,
    # whereas the downloaded dashboard contains JSON numbers.
    assert fingerprint(dashboard)==fingerprint(json.loads(json_bytes(dashboard_data())))
    with sql_connection() as connection:
        with connection.cursor() as cursor:
            for name,count in evidence['row_counts'].items():
                if name not in {'dim_station','fct_station_usage','mart_station_year','mart_canton_year','mart_common_cohort_year'}:
                    raise ValueError('Unexpected table name')
                cursor.execute(f'SELECT COUNT(*) FROM analytics.[{name}]')
                assert cursor.fetchone()[0]==count
    html=client.download_blob(prefix+'dashboard.html').readall()
    assert html==client.download_blob('swiss-rail/dashboard/current.html').readall()
    assert b'Swiss Rail Observatory' in html
    (ROOT/'dashboard/index.html').write_bytes(html)
    (ROOT/'evidence/dashboard-data.json').write_bytes(json_bytes(dashboard))
    (ROOT/'evidence/cloud-run.json').write_bytes(json_bytes(evidence))
    (ROOT/'evidence/cloud-execution.json').write_bytes(json_bytes(execution))
    result=dict(verified_at=datetime.now(timezone.utc).isoformat(),execution_name=expected,execution_status='Succeeded',cloud_run_id=run_id,source_sha256=evidence['source']['sha256'],warehouse_counts=evidence['row_counts'],warehouse_matches_cloud_dashboard=True,dashboard_sha256=hashlib.sha256(html).hexdigest(),authentication='Managed identity inside Azure Container Apps; Azure CLI used only for independent verification')
    (ROOT/'evidence/cloud-verification.json').write_bytes(json_bytes(result))
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    fetch()
