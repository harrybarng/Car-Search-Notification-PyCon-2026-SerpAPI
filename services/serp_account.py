from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_ACCOUNT_URL = "https://serpapi.com/account.json"
_CACHE_TTL = timedelta(minutes=5)

# In-memory cache — no need to persist this to disk
_cache: dict[str, Any] | None = None
_cache_at: datetime | None = None


def fetch_account_info() -> dict[str, Any] | None:
    """
    Fetch SerpAPI account usage. This endpoint is free and does not consume
    search credits. Results are cached in-memory for 5 minutes.
    Returns None if the key is missing or the request fails.
    """
    global _cache, _cache_at

    if _cache is not None and _cache_at is not None:
        if datetime.utcnow() - _cache_at < _CACHE_TTL:
            return _cache

    key = os.environ.get("SERPAPI_KEY", "")
    if not key:
        return None

    try:
        resp = httpx.get(_ACCOUNT_URL, params={"api_key": key}, timeout=8.0)
        resp.raise_for_status()
        data = resp.json()
        # Never expose the raw api_key value in the returned dict
        data.pop("api_key", None)
        _cache = data
        _cache_at = datetime.utcnow()
        return data
    except Exception:
        logger.exception("Failed to fetch SerpAPI account info.")
        return None


def invalidate_cache() -> None:
    global _cache, _cache_at
    _cache = None
    _cache_at = None
