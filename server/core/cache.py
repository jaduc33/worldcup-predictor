"""Tiny JSON file cache with TTL — keeps API-Football calls inside the free quota."""

import json
import time
from pathlib import Path
from typing import Any, Callable

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"


def cached(key: str, ttl_seconds: float, fetch: Callable[[], Any]) -> Any:
    """Return cached JSON for `key` if younger than ttl_seconds, else call fetch() and store it."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.json"

    if path.exists():
        entry = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - entry["cached_at"] < ttl_seconds:
            return entry["data"]

    result = fetch()
    path.write_text(
        json.dumps({"cached_at": time.time(), "data": result}, ensure_ascii=False),
        encoding="utf-8",
    )
    return result
