"""Fetch a complete immutable SBB snapshot and its attribution metadata."""
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request

BASE = "https://data.sbb.ch/api/explore/v2.1/catalog/datasets/passagierfrequenz"
ROOT = Path(__file__).resolve().parents[1]


def get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "ZoomcampSwissRailPortfolio/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read(20_000_001)
    if len(payload) > 20_000_000:
        raise ValueError("Unexpectedly large source response")
    if payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)
    return json.loads(payload)


def extract():
    metadata = get_json(BASE)
    records = get_json(BASE + "/exports/json")
    if not isinstance(records, list) or len(records) != metadata["metas"]["default"]["records_count"]:
        raise ValueError("Incomplete source export or metadata changed during extraction; retry")
    required = {"code_codice", "uic", "jahr_annee_anno", "bahnhof_gare_stazione", "kt_ct_cantone", "dtv_tjm_tgm", "dwv_tmjo_tfm", "dnwv_tmjno_tmgnl"}
    if not records or any(not required.issubset(record) for record in records):
        raise ValueError("Required source fields missing")
    keys = [(r["code_codice"], r["jahr_annee_anno"]) for r in records]
    if len(set(keys)) != len(keys) or any(not all(key) for key in keys):
        raise ValueError("Station-code/year grain is no longer unique and non-null")
    records.sort(key=lambda r:(str(r["code_codice"]),str(r["jahr_annee_anno"])))
    payload = json.dumps(records, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    digest = hashlib.sha256(payload).hexdigest()
    directory = ROOT / "runtime" / "snapshots"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{digest}.json"
    path.write_bytes(payload)
    info = dict(fetched_at=datetime.now(timezone.utc).isoformat(), source_url=BASE+"/exports/json", sha256=digest, rows=len(records), bytes=len(payload), counts_by_year=dict(sorted(Counter(str(r["jahr_annee_anno"]) for r in records).items())), publisher=metadata["metas"]["default"]["publisher"], license=metadata["metas"]["dcat_ap_ch"], source_modified=metadata["metas"]["default"]["modified"], grain="station code and reference year", metrics="Average daily boardings plus alightings, not unique passengers or annual totals")
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "source-profile.json").write_text(json.dumps(info, ensure_ascii=False, indent=2)+"\n")
    return path, info


if __name__ == "__main__":
    _, profile = extract()
    print(json.dumps(profile, indent=2, ensure_ascii=False))
