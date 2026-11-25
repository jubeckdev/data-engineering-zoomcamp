"""Verify keyless ADLS access with an isolated upload/download/delete test."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import uuid


def command(*args):
    return subprocess.check_output(args, text=True, timeout=180).strip()


def main():
    account = command('terraform', 'output', '-raw', 'storage_account_name')
    group = command('terraform', 'output', '-raw', 'resource_group_name')
    settings = json.loads(command('az', 'storage', 'account', 'show', '-n', account, '-g', group,
        '--query', '{hns:isHnsEnabled,sharedKeys:allowSharedKeyAccess,anonymous:allowBlobPublicAccess,location:location}', '-o', 'json'))
    assert settings['hns'] and settings['sharedKeys'] is False and settings['anonymous'] is False
    layers = json.loads(command('az', 'storage', 'fs', 'list', '--account-name', account,
        '--auth-mode', 'login', '--query', '[].name', '-o', 'json'))
    assert sorted(layers) == ['bronze', 'gold', 'silver']
    name = f'checks/{uuid.uuid4().hex}.json'
    content = b'{"purpose":"infrastructure smoke test","synthetic":true}\n'
    with tempfile.TemporaryDirectory() as directory:
        source, downloaded = Path(directory)/'source.json', Path(directory)/'downloaded.json'
        source.write_bytes(content)
        common = ['--account-name', account, '--container-name', 'bronze', '--name', name, '--auth-mode', 'login']
        command('az', 'storage', 'blob', 'upload', *common, '--file', str(source), '--overwrite', 'false', '-o', 'none')
        try:
            command('az', 'storage', 'blob', 'download', *common, '--file', str(downloaded), '-o', 'none')
            assert downloaded.read_bytes() == content, 'Downloaded bytes differ'
        finally:
            command('az', 'storage', 'blob', 'delete', *common, '-o', 'none')
    evidence = {'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'storage_account': account,
                'settings': settings, 'filesystems': sorted(layers), 'authentication': 'Azure CLI / Entra ID',
                'roundtrip_sha256': hashlib.sha256(content).hexdigest(), 'roundtrip_passed': True,
                'test_blob_deleted': True, 'compute_deployed': False}
    Path('verification.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
