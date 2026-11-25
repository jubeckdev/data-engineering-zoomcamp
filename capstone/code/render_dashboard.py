"""Produce a portable, credential-free dashboard from verified serving data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render(data):
    # Prevent dataset strings from terminating the non-executable JSON script.
    payload = json.dumps(data, ensure_ascii=False, default=str).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = (ROOT / 'dashboard/template.html').read_text()
    return template.replace('__DATA_JSON__', payload).encode()


if __name__ == '__main__':
    data = json.loads((ROOT/'evidence/dashboard-data.json').read_text())
    (ROOT/'dashboard/index.html').write_bytes(render(data))
