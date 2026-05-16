from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from serpapi.core import Client as SerpApiClient

from services.cache import get_cached, is_cache_fresh, set_cache
from services.dealers import load_dealers
from services.filter import filter_results_for_criterion
from services.mock_data import get_mock_results
from services.models import Criterion, Dealer
from services.storage import add_match, load_criteria, load_settings

_DEBUG_FILE = Path(__file__).parent.parent / "data" / "debug_last_search.json"

logger = logging.getLogger(__name__)


def _dealer_cache_key(domain: str, make: str, model: str) -> str:
    return f"dealer_{domain}_{make}_{model}".lower().replace(" ", "_")


def _run_google_query(
    query: str,
    api_key: str,
    seen_urls: set[str],
    label: str = "",
) -> list[dict[str, Any]]:
    """Execute a single Google query and return deduplicated organic results."""
    params: dict[str, Any] = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": 10,
        "hl": "en",
        "gl": "us",
    }
    results: list[dict[str, Any]] = []
    try:
        api_key = params.pop("api_key", "")
        data = SerpApiClient(api_key=api_key).search(params)
        if "error" in data:
            logger.warning("Google query error (%s): %s", label, data["error"])
            return results
        for r in data.get("organic_results", []):
            url = r.get("link", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                results.append(r)
        logger.info("Query '%s': %d results", label or query[:60], len(results))
    except Exception as exc:
        logger.warning("Google query failed (%s): %s", label, exc)
    return results


def _fetch_dealer_results(
    dealer: Dealer,
    make: str,
    model: str,
    api_key: str,
    seen_urls: set[str],
) -> list[dict[str, Any]]:
    """
    Two-step search per dealer:
    1. site:{domain} — works when the dealer has server-rendered, indexed inventory pages.
    2. Dealer-name fallback — when site: returns nothing (JS-rendered / hash-URL inventory),
       search for the dealer by name on national listing platforms which index individual pages.
    """
    # Step 1: direct site search. Exclude known non-inventory subdomains so Google
    # doesn't fill all 10 slots with parts/service pages instead of vehicle listings.
    excluded = " ".join(
        f"-site:{sub}.{dealer.domain}"
        for sub in ("parts", "service", "collision", "accessories")
    )
    site_query = f'site:{dealer.domain} {excluded} {model} used OR "pre-owned" OR preowned'
    site_results = _run_google_query(site_query, api_key, seen_urls, label=f"{dealer.domain} (site)")

    # Always run platform search too — national platforms index every listing reliably
    # regardless of how the dealer's own site renders inventory.
    name_query = f'"{dealer.name}" {make} {model} used OR "pre-owned" OR preowned for sale'
    platform_results = _run_google_query(name_query, api_key, seen_urls, label=f"{dealer.name} (platforms)")

    return site_results + platform_results


def estimate_search_calls() -> dict[str, Any]:
    """
    Returns a breakdown of what the next search run will cost.
    Criteria sharing the same (zip, make, model) are batched — one set of
    dealer searches covers all of them.
    """
    settings = load_settings()
    criteria = load_criteria()

    if settings.mock_mode:
        return {"mock": True, "live_calls": 0, "cached": 0, "total_dealers": 0,
                "groups": [], "warnings": []}

    warnings: list[str] = []
    seen_groups: dict[tuple[str, str, str], dict[str, Any]] = {}

    for criterion in criteria:
        if not criterion.zip_code:
            warnings.append(
                f"{criterion.make} {criterion.model}: no zip code — will be skipped"
            )
            continue

        group_key = (criterion.zip_code, criterion.make, criterion.model)
        if group_key in seen_groups:
            seen_groups[group_key]["criteria_count"] += 1
            continue

        dealers = load_dealers(criterion.zip_code, criterion.make)
        if not dealers:
            warnings.append(
                f"{criterion.make} {criterion.model} near {criterion.zip_code}: "
                f"no dealers discovered — go to 🏪 Dealers first"
            )

        dealer_info = [
            {
                "name": d.name,
                "domain": d.domain,
                # 2 calls per dealer: site: search + platform name search
                "cached": is_cache_fresh(
                    _dealer_cache_key(d.domain, criterion.make, criterion.model),
                    settings.cache_ttl_hours,
                ),
                "calls_per_dealer": 2,
            }
            for d in dealers
        ]

        seen_groups[group_key] = {
            "zip": criterion.zip_code,
            "make": criterion.make,
            "model": criterion.model,
            "criteria_count": 1,
            "dealers": dealer_info,
        }

    groups = list(seen_groups.values())
    live_calls = sum(not d["cached"] for g in groups for d in g["dealers"])
    cached = sum(d["cached"] for g in groups for d in g["dealers"])

    return {
        "mock": False,
        "live_calls": live_calls,
        "cached": cached,
        "total_dealers": live_calls + cached,
        "groups": groups,
        "warnings": warnings,
    }


def run_search(
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> tuple[int, list[str], bool]:
    """
    Dealer-based search, grouped by (zip, make, model) to avoid redundant API
    calls when multiple criteria share the same make/model pair.
    Returns (new_match_count, error_messages, used_mock).
    progress_cb(completed, total, dealer_name) is called after each dealer fetch.
    """
    settings = load_settings()
    criteria = load_criteria()

    if not criteria:
        return 0, ["No search criteria defined. Add criteria first."], False

    serp_key = os.environ.get("SERPAPI_KEY", "")
    if not settings.mock_mode and not serp_key:
        return 0, ["SERPAPI_KEY environment variable is not set."], False

    new_count = 0
    errors: list[str] = []
    used_mock = settings.mock_mode
    debug_entries: list[dict[str, Any]] = []

    if settings.mock_mode:
        for criterion in criteria:
            raw = get_mock_results(criterion.make, criterion.model)
            matches = filter_results_for_criterion(raw, criterion, extra_domains=[])
            for match in matches:
                if add_match(match):
                    new_count += 1
        logger.info("Mock search complete. %d new matches.", new_count)
        return new_count, errors, True

    # Group criteria by (zip_code, make, model) — shared dealer searches per group
    groups: dict[tuple[str, str, str], list[Criterion]] = defaultdict(list)
    for criterion in criteria:
        if not criterion.zip_code:
            label = f"{criterion.make} {criterion.model} {criterion.trim or ''}".strip()
            errors.append(
                f"{label}: No zip code set. Add a zip code to enable dealer search."
            )
            continue
        groups[(criterion.zip_code, criterion.make, criterion.model)].append(criterion)

    # Pre-load dealers for all groups so we can give an accurate total to the progress bar.
    group_dealers: dict[tuple[str, str, str], list] = {}
    for key in groups:
        zip_code, make, _ = key
        group_dealers[key] = load_dealers(zip_code, make)

    total_dealers = sum(len(d) for d in group_dealers.values())
    completed_dealers = 0

    for (zip_code, make, model), group_criteria in groups.items():
        dealers = group_dealers[(zip_code, make, model)]
        if not dealers:
            for c in group_criteria:
                label = f"{c.make} {c.model} {c.trim or ''}".strip()
                errors.append(
                    f"{label}: No dealers discovered for {make} near {zip_code}. "
                    f"Go to 🏪 Dealers and run discovery first."
                )
            continue

        # Fetch dealer results once for this (zip, make, model)
        all_results: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        dealer_debug: list[dict[str, Any]] = []

        for dealer in dealers:
            cache_key = _dealer_cache_key(dealer.domain, make, model)
            cached = get_cached(cache_key, settings.cache_ttl_hours, dealer.name)
            if cached is not None:
                added = 0
                for r in cached:
                    url = r.get("link", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(r)
                        added += 1
                dealer_debug.append({"dealer": dealer.name, "domain": dealer.domain,
                                     "source": "cache", "results": added})
            else:
                fresh = _fetch_dealer_results(dealer, make, model, serp_key, seen_urls)
                set_cache(cache_key, fresh, meta={"label": dealer.name})
                all_results.extend(fresh)
                dealer_debug.append({"dealer": dealer.name, "domain": dealer.domain,
                                     "source": "live", "results": len(fresh)})

            completed_dealers += 1
            if progress_cb:
                progress_cb(completed_dealers, total_dealers, dealer.name)

        debug_entries.append({
            "group": f"{make} {model} near {zip_code}",
            "criteria_count": len(group_criteria),
            "dealers": dealer_debug,
            "total_results": len(all_results),
        })

        dealer_domains = [d.domain for d in dealers]
        for criterion in group_criteria:
            matches = filter_results_for_criterion(
                all_results, criterion, extra_domains=dealer_domains, verify_urls=True
            )
            for match in matches:
                if add_match(match):
                    new_count += 1
                    label = f"{make} {model} {criterion.trim or ''}".strip()
                    logger.info("New match: %s — %s", label, match.listing_url)

    with open(_DEBUG_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "search_mode": "dealer",
            "fetched_at": datetime.utcnow().isoformat(),
            "groups": debug_entries,
        }, f, indent=2, default=str)

    logger.info("Search complete. %d new matches.", new_count)
    return new_count, errors, used_mock
