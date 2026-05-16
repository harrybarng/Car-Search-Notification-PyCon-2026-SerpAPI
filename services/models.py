from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class Criterion(BaseModel):
    id: str = Field(default_factory=_new_id)
    make: str
    model: str
    trim: Optional[str] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    mileage_min: Optional[int] = None
    mileage_max: Optional[int] = None
    zip_code: Optional[str] = None
    radius_miles: Optional[int] = 50
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Match(BaseModel):
    id: str = Field(default_factory=_new_id)
    criterion_id: str
    make: str
    model: str
    trim: Optional[str] = None
    price: Optional[int] = None
    year: Optional[int] = None
    mileage: Optional[int] = None
    listing_url: str
    source: Optional[str] = None
    found_at: datetime = Field(default_factory=_now)
    notified: bool = False
    read: bool = False


class Schedule(BaseModel):
    enabled: bool = False
    run_at: str = "08:00"
    buffer_hours: int = 1
    last_run_at: Optional[datetime] = None


class Settings(BaseModel):
    pushover_user_key: str = ""
    pushover_api_token: str = ""
    notifications_enabled: bool = False
    mock_mode: bool = True
    cache_ttl_hours: int = 1
    pages_per_search: int = 1


class Dealer(BaseModel):
    name: str
    domain: str
    address: str = ""
    phone: str = ""
    rating: Optional[float] = None
