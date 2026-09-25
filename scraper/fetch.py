"""Single place for network access so readers stay testable."""
from typing import Optional

import requests

USER_AGENT = ("lunch-lidingo/1.0 (+https://github.com/rstening/lunch-lidingo) "
              "Mozilla/5.0")
TIMEOUT = 20


def get(url: str, headers: Optional[dict] = None) -> bytes:
    merged = {"User-Agent": USER_AGENT}
    if headers:
        merged.update(headers)
    resp = requests.get(url, headers=merged, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.content
