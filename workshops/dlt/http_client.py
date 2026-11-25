"""Bounded retries for public, read-only API calls."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def session():
    client = requests.Session()
    retry = Retry(total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"], respect_retry_after_header=True)
    client.mount("https://", HTTPAdapter(max_retries=retry))
    client.headers["User-Agent"] = "ZoomcampPortfolio/1.0 (educational batch ingestion)"
    return client
