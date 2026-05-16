from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from filelock import FileLock

from services.models import Dealer

logger = logging.getLogger(__name__)

_DEALERS_FILE = Path(__file__).parent.parent / "data" / "dealers.json"


def _lock() -> FileLock:
    return FileLock(str(_DEALERS_FILE) + ".lock")


def _key(zip_code: str, make: str) -> str:
    return f"{zip_code}_{make.lower()}"


def load_all() -> dict[str, Any]:
    """Returns raw storage dict keyed by '{zip}_{make}'."""
    with _lock():
        if not _DEALERS_FILE.exists():
            return {}
        with open(_DEALERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


def _save_all(data: dict[str, Any]) -> None:
    with _lock():
        _DEALERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_DEALERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def load_dealers(zip_code: str, make: str) -> list[Dealer]:
    entry = load_all().get(_key(zip_code, make), {})
    return [Dealer.model_validate(d) for d in entry.get("dealers", [])]


def save_dealers(zip_code: str, make: str, dealers: list[Dealer]) -> None:
    data = load_all()
    data[_key(zip_code, make)] = {
        "zip_code": zip_code,
        "make": make,
        "discovered_at": datetime.utcnow().isoformat(),
        "dealers": [d.model_dump() for d in dealers],
    }
    _save_all(data)


def remove_entry(zip_code: str, make: str) -> None:
    data = load_all()
    data.pop(_key(zip_code, make), None)
    _save_all(data)


def _extract_domain(url: str) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).netloc.lower().removeprefix("www.")
        return host or None
    except Exception:
        return None


def discover_dealers(zip_code: str, make: str, api_key: str) -> tuple[list[Dealer], str | None]:
    """Use SerpAPI google_maps engine to find all make dealerships near zip_code."""
    from serpapi.core import Client as SerpApiClient

    params: dict[str, Any] = {
        "engine": "google_maps",
        "q": f"{make} dealership",
        "location": zip_code,
        "z": "13",
        "api_key": api_key,
        "hl": "en",
        "gl": "us",
        "type": "search",
    }

    try:
        api_key = params.pop("api_key", "")
        data = SerpApiClient(api_key=api_key).search(params)
    except Exception as exc:
        return [], f"SerpAPI request failed: {exc}"

    if "error" in data:
        return [], f"SerpAPI error: {data['error']}"

    dealers: list[Dealer] = []
    seen_domains: set[str] = set()

    for place in data.get("local_results", []):
        website = place.get("website", "")
        domain = _extract_domain(website)
        if not domain or domain in seen_domains:
            continue
        seen_domains.add(domain)
        dealers.append(Dealer(
            name=place.get("title", "Unknown"),
            domain=domain,
            address=place.get("address", ""),
            phone=place.get("phone", ""),
            rating=place.get("rating"),
        ))

    if not dealers:
        return [], f"No {make} dealers found near {zip_code}."

    logger.info(
        "Discovered %d %s dealers near %s: %s",
        len(dealers), make, zip_code, [d.domain for d in dealers],
    )
    return dealers, None
