from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from filelock import FileLock

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"


def _cache_path(key: str) -> Path:
    safe = key.lower().replace(" ", "_")
    return _CACHE_DIR / f"{safe}.json"


def _lock(path: Path) -> FileLock:
    return FileLock(str(path) + ".lock")


def is_cache_fresh(key: str, ttl_hours: int) -> bool:
    """Return True if a fresh cache entry exists for key (no data loaded)."""
    if ttl_hours <= 0:
        return False
    path = _cache_path(key)
    if not path.exists():
        return False
    try:
        with _lock(path):
            with open(path, "r", encoding="utf-8") as f:
                fetched_at = json.load(f).get("fetched_at", "")
        return datetime.utcnow() - datetime.fromisoformat(fetched_at) <= timedelta(hours=ttl_hours)
    except Exception:
        return False


def get_cached(key: str, ttl_hours: int, label: str = "") -> list[dict[str, Any]] | None:
    """Return cached results if within TTL. Returns None if missing or stale."""
    if ttl_hours <= 0:
        return None

    path = _cache_path(key)
    if not path.exists():
        return None

    with _lock(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

    fetched_at = datetime.fromisoformat(data["fetched_at"])
    age = datetime.utcnow() - fetched_at
    if age > timedelta(hours=ttl_hours):
        logger.info("Cache expired for %s (age: %s)", label or key, age)
        return None

    logger.info("Cache hit for %s (%d results, age: %s)", label or key, len(data["results"]), age)
    return data["results"]


def set_cache(key: str, results: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> None:
    """Save raw API results under the given key."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(key)
    payload = {
        "fetched_at": datetime.utcnow().isoformat(),
        "results": results,
        **(meta or {}),
    }
    with _lock(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    logger.info("Cached %d results for key '%s'", len(results), key)


def clear_cache() -> int:
    """Delete all cache files. Returns number of files deleted."""
    if not _CACHE_DIR.exists():
        return 0
    count = 0
    for f in _CACHE_DIR.glob("*.json"):
        f.unlink(missing_ok=True)
        count += 1
    logger.info("Cleared %d cache file(s).", count)
    return count


def cache_status() -> list[dict[str, Any]]:
    """Return a list of cache entries with age and result count."""
    if not _CACHE_DIR.exists():
        return []
    entries = []
    for path in sorted(_CACHE_DIR.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            fetched_at = datetime.fromisoformat(data["fetched_at"])
            age_minutes = int((datetime.utcnow() - fetched_at).total_seconds() / 60)
            entries.append({
                "label": data.get("label", path.stem),
                "results": len(data.get("results", [])),
                "fetched_at": fetched_at,
                "age_minutes": age_minutes,
            })
        except Exception:
            pass
    return entries
