from __future__ import annotations

import logging

import httpx

from services.models import Match
from services.storage import load_settings

logger = logging.getLogger(__name__)

_PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


def send_pushover(matches: list[Match]) -> bool:
    """Send a grouped Pushover notification for new matches. Returns True on success."""
    if not matches:
        return True

    settings = load_settings()
    if not settings.notifications_enabled:
        return False
    if not settings.pushover_user_key or not settings.pushover_api_token:
        logger.warning("Pushover credentials not configured.")
        return False

    count = len(matches)
    makes_models = ", ".join(sorted({f"{m.make} {m.model}" for m in matches}))
    message = f"{count} new match{'es' if count > 1 else ''} found: {makes_models}. Open the app to view."

    try:
        response = httpx.post(
            _PUSHOVER_URL,
            data={
                "token": settings.pushover_api_token,
                "user": settings.pushover_user_key,
                "message": message,
                "title": "Car Search Alert",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        logger.info("Pushover notification sent for %d matches.", count)
        return True
    except httpx.HTTPError:
        logger.exception("Failed to send Pushover notification.")
        return False
