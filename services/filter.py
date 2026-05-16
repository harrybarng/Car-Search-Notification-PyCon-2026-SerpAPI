from __future__ import annotations

import json as _json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import urlparse

import httpx

_PATH_WORD_RE = re.compile(r"[/_-]")

from services.models import Criterion, Match

# Known car listing platforms — accept any URL from these domains.
_CAR_PLATFORMS = {
    "autotrader.com", "cargurus.com", "cars.com", "carvana.com",
    "carmax.com", "truecar.com", "edmunds.com", "vroom.com",
    "carfax.com", "autonation.com", "dealer.com",
}

# URL path segments that indicate a non-vehicle page on a dealer site.
_BLOCKED_PATH_SEGMENTS = {
    "parts", "accessories", "service", "repair", "collision", "tires",
    "finance", "financing", "specials", "careers", "team", "about",
    "contact", "reviews", "blog", "news", "events", "gallery",
}

# Subdomains that indicate a non-vehicle section of a dealer site.
_BLOCKED_SUBDOMAINS = {"parts", "service", "collision", "accessories", "bodyshop"}

logger = logging.getLogger(__name__)

_YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-2]\d)\b")
_PRICE_RE = re.compile(r"\$\s*([\d,]+)")
_MILEAGE_RE = re.compile(
    r"([\d,]+)\s*k\s*(?:miles?|mi)\b"   # 34k miles / 34k mi
    r"|([\d,]+),(\d{3})\s*(?:miles?|mi)" # 34,000 miles
    r"|([\d,]+)\s*(?:miles?|mi)\b",      # 34000 miles / 34 mi (low mileage fallback)
    re.IGNORECASE,
)


def _parse_price(text: str) -> int | None:
    # Try all $ matches and return the most plausible car price (5k–500k range)
    for m in _PRICE_RE.finditer(text):
        try:
            value = int(m.group(1).replace(",", ""))
            if 5_000 <= value <= 500_000:
                return value
        except ValueError:
            pass
    return None


def _parse_year(text: str) -> int | None:
    m = _YEAR_RE.search(text)
    return int(m.group(0)) if m else None


def _parse_mileage(text: str) -> int | None:
    for m in _MILEAGE_RE.finditer(text):
        try:
            if m.group(1):               # "34k miles" form
                value = int(m.group(1).replace(",", "")) * 1000
            elif m.group(2):             # "34,000 miles" form
                value = int(m.group(2).replace(",", "")) * 1000 + int(m.group(3))
            else:                        # "34000 miles" plain form
                raw = (m.group(4) or "").replace(",", "")
                value = int(raw)
            # Sanity check: skip implausible values (e.g. years parsed as mileage)
            if 100 <= value <= 500_000:
                return value
        except (ValueError, TypeError):
            pass
    return None


def _extract_fields(result: dict[str, Any]) -> dict[str, Any]:
    """Extract structured fields from a Google organic result dict."""
    title = result.get("title", "")
    snippet = result.get("snippet", "") or ""
    # rich_snippet gives structured data when Google extracts it
    rich = result.get("rich_snippet", {}) or {}
    rich_text = " ".join(str(v) for v in rich.values()) if rich else ""
    blob = f"{title} {snippet} {rich_text}"

    price = _parse_price(blob)
    year = _parse_year(blob)
    mileage = _parse_mileage(blob)
    url = result.get("link", "")
    source = result.get("displayed_link", "") or result.get("source", "")

    if price is None:
        logger.debug("Could not parse price from: %s", blob[:120])
    if year is None:
        logger.debug("Could not parse year from: %s", title)
    if mileage is None:
        logger.debug("Could not parse mileage from: %s", blob[:120])

    return {
        "price": price,
        "year": year,
        "mileage": mileage,
        "url": url,
        "source": source,
        "title": title,
        "snippet": snippet,
    }


def _matches_criterion(fields: dict[str, Any], criterion: Criterion) -> bool:
    searchable = f"{fields['title']} {fields['snippet']}".lower()

    # Model must appear in title or snippet — blocks wrong-model results (Q5 for A4 query)
    # where Google returns a page that only mentions A4 in the navigation.
    if criterion.model.lower() not in searchable:
        return False

    # Trim: only reject if the snippet explicitly names a *different* trim.
    # Dealer page snippets often omit the trim entirely — don't penalise that.
    # National platform snippets usually include trim, so the check still bites there.
    if criterion.trim:
        trim_lower = criterion.trim.lower()
        # Words in the trim string that distinguish it from other trims
        trim_words = set(trim_lower.split())
        snippet_has_any_trim_word = any(w in searchable for w in trim_words if len(w) > 3)
        if snippet_has_any_trim_word and trim_lower not in searchable:
            # Snippet mentions trim-like words but not our specific trim → different trim
            return False

    price = fields["price"]
    if price is not None:
        if criterion.price_min is not None and price < criterion.price_min:
            return False
        if criterion.price_max is not None and price > criterion.price_max:
            return False

    year = fields["year"]
    if year is not None:
        if criterion.year_min is not None and year < criterion.year_min:
            return False
        if criterion.year_max is not None and year > criterion.year_max:
            return False

    mileage = fields["mileage"]
    if mileage is not None:
        if criterion.mileage_min is not None and mileage < criterion.mileage_min:
            return False
        if criterion.mileage_max is not None and mileage > criterion.mileage_max:
            return False

    return True


_SOLD_RE = re.compile(
    r"\bsold\b|no longer available|listing.*expired|"
    r"vehicle.*sold|not available|listing not found",
    re.IGNORECASE,
)

_SOLD_PAGE_RE = re.compile(
    r"no longer available|vehicle has been sold|listing.*expired|"
    r"this vehicle is not available|vehicle not found|inventory not found|"
    r"this page (does not exist|could not be found)|listing not found|"
    r"this listing is no longer|unfortunately.*page|page.*not found",
    re.IGNORECASE,
)

_HTTP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _is_sold_in_snippet(title: str, snippet: str) -> bool:
    return bool(_SOLD_RE.search(f"{title} {snippet}"))


_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


def _extract_from_jsonld(html: str) -> dict[str, Any]:
    """Pull price, mileage, year from schema.org/Vehicle JSON-LD blocks."""
    for m in _JSONLD_RE.finditer(html):
        try:
            data = _json.loads(m.group(1))
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            type_ = str(item.get("@type", ""))
            if not any(t in type_ for t in ("Vehicle", "Car", "Product")):
                continue

            price: int | None = None
            mileage: int | None = None
            year: int | None = None

            offers = item.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            raw_price = offers.get("price") if isinstance(offers, dict) else None
            if raw_price is not None:
                try:
                    price = int(float(str(raw_price).replace(",", "")))
                    if not (5_000 <= price <= 500_000):
                        price = None
                except (ValueError, TypeError):
                    price = None

            odometer = item.get("mileageFromOdometer") or {}
            if isinstance(odometer, dict):
                raw_mi = odometer.get("value")
                if raw_mi is not None:
                    try:
                        mileage = int(float(str(raw_mi).replace(",", "")))
                        if not (100 <= mileage <= 500_000):
                            mileage = None
                    except (ValueError, TypeError):
                        mileage = None

            for key in ("modelDate", "vehicleModelDate", "productionDate"):
                raw_year = item.get(key)
                if raw_year:
                    try:
                        year = int(str(raw_year)[:4])
                        break
                    except (ValueError, TypeError):
                        pass

            if price or mileage or year:
                return {"price": price, "mileage": mileage, "year": year}
    return {}


def _fetch_listing_data(url: str) -> tuple[bool, dict[str, Any]]:
    """Fetch the listing URL. Returns (is_sold, {price, mileage, year}).

    Combines the availability check with structured-data extraction so we
    make only one HTTP request per candidate listing.
    """
    empty: dict[str, Any] = {"price": None, "mileage": None, "year": None}
    try:
        with httpx.Client(
            timeout=5.0,
            follow_redirects=True,
            headers={"User-Agent": _HTTP_UA},
        ) as client:
            resp = client.get(url)

        if resp.status_code == 404:
            return True, empty

        # Redirect to the site root means the listing page is gone.
        original_path = urlparse(url).path.rstrip("/")
        final_path = str(resp.url.path).rstrip("/")
        if final_path != original_path and len(final_path) <= 1:
            return True, empty

        html = resp.text
        if _SOLD_PAGE_RE.search(html[:8_000]):
            return True, empty

        extracted = _extract_from_jsonld(html)
        # Fallback: reuse existing regex parsers on a broader slice of the HTML
        if not extracted.get("price"):
            extracted["price"] = extracted.get("price") or _parse_price(html[:20_000])
        if not extracted.get("mileage"):
            extracted["mileage"] = extracted.get("mileage") or _parse_mileage(html[:20_000])
        if not extracted.get("year"):
            extracted["year"] = extracted.get("year") or _parse_year(html[:5_000])

        return False, extracted
    except Exception:
        return False, empty  # On error, keep the result rather than over-filtering



_NEW_CAR_RE = re.compile(r"\bnew\b", re.IGNORECASE)
_NEW_CAR_TITLE_RE = re.compile(r"^\s*new\s+\d{4}\b", re.IGNORECASE)
_USED_RE = re.compile(r"\b(used|pre.?owned|preowned|certified)\b", re.IGNORECASE)


def _is_new_car(title: str, snippet: str) -> bool:
    """Return True if the listing is clearly a new (not used) vehicle."""
    # Title starting with "New 2024 …" is a definitive new-car signal regardless of snippet.
    if _NEW_CAR_TITLE_RE.match(title):
        return True
    blob = f"{title} {snippet}"
    return bool(_NEW_CAR_RE.search(blob)) and not bool(_USED_RE.search(blob))


def _is_parts_or_service_url(url: str) -> bool:
    """Return True if the URL subdomain or path clearly points to a parts/service page."""
    try:
        parsed = urlparse(url)
        # Check subdomain (e.g. parts.audipaloalto.com)
        host_parts = parsed.netloc.lower().split(".")
        if len(host_parts) > 2 and host_parts[0] in _BLOCKED_SUBDOMAINS:
            return True
        # Split path by /, -, _ so "specials-and-finance" is caught as "specials"
        words = set(_PATH_WORD_RE.split(parsed.path.lower()))
        return bool(words & _BLOCKED_PATH_SEGMENTS)
    except Exception:
        return False


_PLATFORM_ID_RE = re.compile(r"(\d{6,}|[A-Z0-9]{10,})", re.IGNORECASE)


def _is_listing_url(url: str, extra_domains: frozenset[str] = frozenset()) -> bool:
    try:
        host = urlparse(url).netloc.lower().removeprefix("www.")
        allowed = _CAR_PLATFORMS | extra_domains
        if not any(host == d or host.endswith("." + d) for d in allowed):
            return False
        # Individual listing pages — on both national platforms and dealer sites —
        # always have a vehicle-specific ID or model year in the URL.
        # Browse/category/city pages (e.g. /inventory/used, /Used_Cars/San_Jose_CA/Audi)
        # have neither, so we block them here.
        parsed = urlparse(url)
        url_path = parsed.path + "?" + parsed.query
        has_id = bool(_PLATFORM_ID_RE.search(url_path))
        has_year = bool(_YEAR_RE.search(parsed.path))
        if not (has_id or has_year):
            return False
        return True
    except Exception:
        return False


def filter_results_for_criterion(
    raw_results: list[dict[str, Any]],
    criterion: Criterion,
    extra_domains: list[str] | None = None,
    verify_urls: bool = False,
) -> list[Match]:
    """Filter raw Google organic results against a single criterion.

    verify_urls=True fetches each candidate URL to confirm the vehicle is still listed.
    """
    candidates: list[Match] = []
    allowed_extra = frozenset(extra_domains) if extra_domains else frozenset()

    for result in raw_results:
        fields = _extract_fields(result)
        if not fields["url"]:
            continue
        if not _is_listing_url(fields["url"], allowed_extra):
            logger.debug("Skipping non-listing URL: %s", fields["url"])
            continue
        if _is_parts_or_service_url(fields["url"]):
            logger.debug("Skipping parts/service URL: %s", fields["url"])
            continue
        if _is_new_car(fields["title"], fields["snippet"]):
            logger.debug("Skipping new-car listing: %s", fields["url"])
            continue
        # Any result without a parseable year is a browse/category page, not a listing.
        # Individual vehicle pages on both dealer sites and national platforms always
        # include the model year in the title or snippet.
        if fields["year"] is None:
            logger.debug("Skipping result without year (browse page): %s", fields["url"])
            continue
        if _is_sold_in_snippet(fields["title"], fields["snippet"]):
            logger.debug("Snippet indicates sold, skipping: %s", fields["url"])
            continue
        if not _matches_criterion(fields, criterion):
            continue
        candidates.append(Match(
            criterion_id=criterion.id,
            make=criterion.make,
            model=criterion.model,
            trim=fields["title"],
            price=fields["price"],
            year=fields["year"],
            mileage=fields["mileage"],
            listing_url=fields["url"],
            source=fields["source"],
        ))

    if not verify_urls or not candidates:
        return candidates

    # Fetch each candidate URL concurrently: confirm availability + extract missing fields.
    workers = min(8, len(candidates))
    available: list[Match] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_match = {
            pool.submit(_fetch_listing_data, m.listing_url): m for m in candidates
        }
        for fut in as_completed(future_to_match):
            m = future_to_match[fut]
            is_sold, extracted = fut.result()
            if is_sold:
                logger.info("Skipping sold/unavailable listing: %s", m.listing_url)
                continue
            # Fill in fields the Google snippet didn't include
            updates: dict[str, Any] = {}
            if m.price is None and extracted.get("price"):
                updates["price"] = extracted["price"]
            if m.mileage is None and extracted.get("mileage"):
                updates["mileage"] = extracted["mileage"]
            if m.year is None and extracted.get("year"):
                updates["year"] = extracted["year"]
            available.append(m.model_copy(update=updates) if updates else m)

    return available
