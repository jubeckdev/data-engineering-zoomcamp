"""Import trusted local flows or execute one and wait for completion."""
import argparse
import base64
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get('KESTRA_URL','http://127.0.0.1:8082') + '/api/v1/main'
AUTH = base64.b64encode(os.environ.get('KESTRA_AUTH','admin@local.test:LocalZoomcamp123!').encode()).decode()


def request(path, fields=None):
    headers = {'Authorization':f'Basic {AUTH}'}
    data = None
    if fields is not None:
        boundary = uuid.uuid4().hex
        parts = []
        for name, value, filename in fields:
            disposition = f'Content-Disposition: form-data; name="{name}"'
            if filename:
                disposition += f'; filename="{filename}"'
            parts.append(f'--{boundary}\r\n{disposition}\r\n\r\n'.encode() + value + b'\r\n')
        data = b''.join(parts) + f'--{boundary}--\r\n'.encode()
        headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers),timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(error.read().decode()) from error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['import','run'])
    parser.add_argument('--flow',default='taxi_month')
    parser.add_argument('--taxi',choices=['green','yellow'],default='green')
    parser.add_argument('--year',default='2021')
    parser.add_argument('--month',default='01')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--timeout',type=int,default=1800)
    args = parser.parse_args()
    if args.action == 'import':
        for flow in sorted((Path(__file__).resolve().parent.parent/'flows').glob('*.yaml')):
            print(flow.name,request('/flows/import',[('fileUpload',flow.read_bytes(),flow.name)]))
        return
    inputs = [('taxi',args.taxi.encode(),None),('year',args.year.encode(),None),('month',args.month.encode(),None)] if args.flow == 'taxi_month' else []
    execution = request(f'/executions/zoomcamp.module2/{args.flow}',inputs)
    print('Execution:',execution['id'],flush=True)
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        execution = request('/executions/'+execution['id'])
        state = execution['state']['current']
        if state in ['SUCCESS','FAILED','KILLED','CANCELLED','WARNING']:
            if args.output:
                args.output.parent.mkdir(parents=True,exist_ok=True)
                args.output.write_text(json.dumps(execution,indent=2)+'\n')
            print('Final state:',state,flush=True)
            if state != 'SUCCESS':
                raise SystemExit(1)
            return
        time.sleep(3)
    raise TimeoutError('Execution still running; inspect Kestra UI before retrying')


if __name__ == '__main__':
    main()
