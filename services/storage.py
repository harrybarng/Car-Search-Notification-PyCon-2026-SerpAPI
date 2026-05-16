from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from filelock import FileLock
from pydantic import BaseModel

from services.models import Criterion, Match, Schedule, Settings

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

_CRITERIA_FILE = DATA_DIR / "criteria.json"
_MATCHES_FILE = DATA_DIR / "matches.json"
_SCHEDULE_FILE = DATA_DIR / "schedule.json"
_SETTINGS_FILE = DATA_DIR / "settings.json"
_DEALERS_FILE = DATA_DIR / "dealers.json"


def ensure_data_files() -> None:
    """Create the data directory and all required JSON files if they don't exist.
    Safe to call on every startup — skips files that already exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    defaults: dict[Path, Any] = {
        _CRITERIA_FILE: [],
        _MATCHES_FILE: [],
        _SCHEDULE_FILE: {"enabled": False, "run_at": "08:00", "buffer_hours": 1, "last_run_at": None},
        _SETTINGS_FILE: {
            "pushover_user_key": "",
            "pushover_api_token": "",
            "notifications_enabled": False,
            "mock_mode": True,
            "cache_ttl_hours": 1,
            "pages_per_search": 1,
        },
        _DEALERS_FILE: {},
    }

    for path, default in defaults.items():
        if not path.exists():
            with _lock(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(default, f, indent=2)
            logger.info("Created missing data file: %s", path.name)


def _lock(path: Path) -> FileLock:
    return FileLock(str(path) + ".lock")


def _read_json(path: Path) -> Any:
    with _lock(path):
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def _write_json(path: Path, data: Any) -> None:
    with _lock(path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)


# --- Criteria ---

def load_criteria() -> list[Criterion]:
    raw = _read_json(_CRITERIA_FILE)
    if not raw:
        return []
    return [Criterion.model_validate(c) for c in raw]


def save_criteria(criteria: list[Criterion]) -> None:
    _write_json(_CRITERIA_FILE, [c.model_dump(mode="json") for c in criteria])


def add_criterion(criterion: Criterion) -> None:
    criteria = load_criteria()
    criteria.append(criterion)
    save_criteria(criteria)


def update_criterion(criterion: Criterion) -> None:
    criteria = load_criteria()
    criteria = [c if c.id != criterion.id else criterion for c in criteria]
    save_criteria(criteria)


def delete_criterion(criterion_id: str) -> None:
    criteria = load_criteria()
    criteria = [c for c in criteria if c.id != criterion_id]
    save_criteria(criteria)


# --- Matches ---

def load_matches() -> list[Match]:
    raw = _read_json(_MATCHES_FILE)
    if not raw:
        return []
    return [Match.model_validate(m) for m in raw]


def save_matches(matches: list[Match]) -> None:
    _write_json(_MATCHES_FILE, [m.model_dump(mode="json") for m in matches])


def add_match(match: Match) -> bool:
    """Returns True if the match was new and saved, False if duplicate."""
    matches = load_matches()
    urls = {m.listing_url for m in matches}
    if match.listing_url in urls:
        return False
    matches.append(match)
    save_matches(matches)
    return True


def mark_all_read() -> None:
    matches = load_matches()
    for m in matches:
        m.read = True
    save_matches(matches)


def unread_count() -> int:
    return sum(1 for m in load_matches() if not m.read)


# --- Schedule ---

def load_schedule() -> Schedule:
    raw = _read_json(_SCHEDULE_FILE)
    if not raw:
        return Schedule()
    return Schedule.model_validate(raw)


def save_schedule(schedule: Schedule) -> None:
    _write_json(_SCHEDULE_FILE, schedule.model_dump(mode="json"))


# --- Settings ---

def load_settings() -> Settings:
    raw = _read_json(_SETTINGS_FILE)
    if not raw:
        return Settings()
    return Settings.model_validate(raw)


def save_settings(settings: Settings) -> None:
    _write_json(_SETTINGS_FILE, settings.model_dump(mode="json"))
