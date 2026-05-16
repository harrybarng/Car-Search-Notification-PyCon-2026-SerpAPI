from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from components.section_header import section_header
from components.status_indicator import status_indicator
from services.cache import cache_status, clear_cache
from services.models import Settings
from services.serp_account import fetch_account_info
from services.storage import load_settings, save_settings


def _autosave_search_settings(mock_mode: bool, cache_ttl: int, pages_per_search: int) -> None:
    """Persist search behaviour fields immediately on widget change."""
    current = load_settings()
    if (
        current.mock_mode != mock_mode
        or current.cache_ttl_hours != cache_ttl
        or current.pages_per_search != pages_per_search
    ):
        updated = Settings(
            mock_mode=mock_mode,
            cache_ttl_hours=cache_ttl,
            pages_per_search=pages_per_search,
            notifications_enabled=current.notifications_enabled,
            pushover_user_key=current.pushover_user_key,
            pushover_api_token=current.pushover_api_token,
        )
        save_settings(updated)


def render() -> None:
    section_header("Settings", "Search behaviour, notifications, and developer tools")

    settings = load_settings()

    # ------------------------------------------------------------------ #
    # Search behaviour — auto-saved on change so navigation never resets them
    # ------------------------------------------------------------------ #
    st.markdown("### Search Behaviour")

    mock_mode = st.toggle(
        "Mock mode (simulate results — no API calls)",
        value=settings.mock_mode,
        key="toggle_mock_mode",
        help="When on, searches return realistic fake data and consume zero SerpAPI calls. "
             "Turn off when you're ready to validate against live listings.",
    )

    if mock_mode:
        st.info("Mock mode is **on**. All searches use simulated listings. No SerpAPI calls will be made.")
    else:
        st.warning("Mock mode is **off**. Searches will hit the live SerpAPI and consume your monthly quota.")

    st.markdown("")

    cache_ttl = st.number_input(
        "Cache TTL (hours)",
        min_value=0,
        max_value=168,
        value=settings.cache_ttl_hours,
        step=1,
        key="input_cache_ttl",
        disabled=mock_mode,
        help="How long to reuse a previous API result before fetching fresh data. "
             "Set to 0 to disable caching. Has no effect while mock mode is on.",
    )

    if not mock_mode:
        if cache_ttl == 0:
            st.warning("Cache TTL is 0 — every search run will make a live API call.")
        else:
            st.caption(
                f"Each make/model pair fetched live at most once every {cache_ttl} hour(s). "
                "Searches within that window read from cache and use 0 API calls."
            )

    st.markdown("")

    pages_per_search = st.number_input(
        "Pages per search",
        min_value=1,
        max_value=5,
        value=settings.pages_per_search,
        step=1,
        key="input_pages_per_search",
        help="Each page fetches 10 results and counts as 1 SerpAPI call. "
             "Higher values find more listings but use more of your monthly quota.",
    )
    st.caption(
        f"{pages_per_search} page(s) × 10 results = up to {pages_per_search * 10} listings per criterion per run. "
        f"Each page = 1 API call."
    )

    # Auto-save search behaviour immediately — no Save button needed
    _autosave_search_settings(mock_mode, int(cache_ttl), int(pages_per_search))

    st.markdown("")

    # ------------------------------------------------------------------ #
    # SerpAPI monthly usage
    # ------------------------------------------------------------------ #
    st.markdown("### SerpAPI Monthly Usage")

    acct = fetch_account_info()
    if acct is None:
        st.caption("Set a valid SERPAPI_KEY in your .env file to see usage stats.")
    else:
        used = acct.get("this_month_usage", 0)
        total = acct.get("searches_per_month", 250)
        left = acct.get("plan_searches_left", total - used)
        rate_limit = acct.get("account_rate_limit_per_hour", 0)
        pct = used / total if total else 0

        # Color thresholds: teal → amber → red
        if pct >= 0.90:
            bar_color = "#F44336"
            label_color = "#F44336"
        elif pct >= 0.70:
            bar_color = "#FFC107"
            label_color = "#F57F17"
        else:
            bar_color = "#009688"
            label_color = "#009688"

        st.markdown(
            f"""
            <div style="margin-bottom:6px;display:flex;justify-content:space-between;align-items:baseline">
                <span style="font-size:0.95rem;color:#212121">
                    <b style="color:{label_color}">{used}</b> / {total} calls used this month
                </span>
                <span style="font-size:0.85rem;color:#757575">{left} remaining</span>
            </div>
            <div style="background:#E0E0E0;border-radius:8px;height:10px;overflow:hidden">
                <div style="
                    background:{bar_color};
                    width:{min(pct*100, 100):.1f}%;
                    height:100%;
                    border-radius:8px;
                    transition:width 0.3s ease;
                "></div>
            </div>
            <div style="margin-top:6px;font-size:0.8rem;color:#757575">
                Plan: {acct.get('plan_name', '—')} &nbsp;·&nbsp;
                {total} searches/month &nbsp;·&nbsp;
                Max {rate_limit} searches/hr &nbsp;·&nbsp;
                {acct.get('account_email', '')}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if pct >= 0.90:
            status_indicator("error", "You've used over 90% of your monthly quota. Enable mock mode to preserve remaining calls.")
        elif pct >= 0.70:
            status_indicator("warning", "You've used over 70% of your monthly quota.")

    st.markdown("")

    # ------------------------------------------------------------------ #
    # Cache status
    # ------------------------------------------------------------------ #
    st.markdown("### Cache")

    entries = cache_status()
    if not entries:
        st.caption("No cache entries yet.")
    else:
        for e in entries:
            if e["age_minutes"] < 60:
                age_str = f"{e['age_minutes']}m ago"
            else:
                age_str = f"{e['age_minutes'] // 60}h {e['age_minutes'] % 60}m ago"
            st.caption(f"**{e['label']}** — {e['results']} results cached, fetched {age_str}")

    if st.button("Clear Cache", disabled=not entries):
        n = clear_cache()
        status_indicator("success", f"Cleared {n} cache file(s).")
        st.rerun()

    st.markdown("")

    # ------------------------------------------------------------------ #
    # Notifications — requires explicit Save because keys are typed one char at a time
    # ------------------------------------------------------------------ #
    st.markdown("### Notifications (Pushover)")

    notifications_enabled = st.toggle(
        "Enable push notifications",
        value=settings.notifications_enabled,
        key="toggle_notifications",
    )

    pushover_user_key = st.text_input(
        "Pushover User Key",
        value=settings.pushover_user_key,
        type="password",
        disabled=not notifications_enabled,
        help="Found on your Pushover dashboard at pushover.net",
    )

    pushover_api_token = st.text_input(
        "Pushover App Token",
        value=settings.pushover_api_token,
        type="password",
        disabled=not notifications_enabled,
        help="Created under 'Your Applications' on pushover.net",
    )

    if notifications_enabled and (not pushover_user_key or not pushover_api_token):
        status_indicator("warning", "Both Pushover fields are required to send notifications.")

    st.markdown("")

    if st.button("Save Notification Settings", type="primary"):
        current = load_settings()
        updated = Settings(
            mock_mode=current.mock_mode,
            cache_ttl_hours=current.cache_ttl_hours,
            notifications_enabled=notifications_enabled,
            pushover_user_key=pushover_user_key.strip(),
            pushover_api_token=pushover_api_token.strip(),
        )
        save_settings(updated)
        status_indicator("success", "Notification settings saved.")

    st.markdown("")

    # ------------------------------------------------------------------ #
    # Debug — raw last search response
    # ------------------------------------------------------------------ #
    st.markdown("### Debug: Last Live Search Response")

    debug_path = Path(__file__).parent.parent / "data" / "debug_last_search.json"
    if not debug_path.exists():
        st.caption("No live search has been run yet. Turn off mock mode and run a search to populate this.")
    else:
        with open(debug_path, "r", encoding="utf-8") as f:
            debug = json.load(f)

        fetched_at = debug.get("fetched_at", "unknown")
        result_count = debug.get("organic_results_count", 0)
        query = debug.get("query", "")
        params_sent = debug.get("params_sent", {})
        search_info = debug.get("search_information", {})
        results = debug.get("organic_results", [])

        st.caption(f"Fetched at: {fetched_at}")

        col1, col2 = st.columns(2)
        col1.metric("Results returned", result_count)
        col2.metric("Requested (num)", params_sent.get("num", "?"))

        st.markdown("**Query sent to Google:**")
        st.code(query, language=None)

        if search_info:
            st.markdown("**Google search information:**")
            st.json(search_info)

        st.markdown(f"**Raw results ({result_count} total) — showing all:**")
        for i, r in enumerate(results):
            with st.expander(f"Result {i+1}: {r.get('title', 'no title')[:80]}", expanded=i == 0):
                st.markdown(f"**URL:** {r.get('link', '—')}")
                st.markdown(f"**Displayed link:** {r.get('displayed_link', '—')}")
                st.markdown(f"**Snippet:** {r.get('snippet', '—')}")
                rich = r.get("rich_snippet")
                if rich:
                    st.markdown("**Rich snippet:**")
                    st.json(rich)
                st.markdown("**All fields:**")
                st.json({k: v for k, v in r.items() if k not in ("title", "link", "displayed_link", "snippet", "rich_snippet")})
