from __future__ import annotations

import streamlit as st

from components.empty_state import empty_state
from components.match_card import match_card
from components.schedule_widget import schedule_widget
from components.section_header import section_header
from components.status_indicator import status_indicator
from services.notify import send_pushover
from services.scheduler import record_manual_run
from services.search import estimate_search_calls, run_search
from services.serp_account import fetch_account_info
from services.storage import load_criteria, load_matches, load_settings, mark_all_read, save_matches


@st.dialog("No dealers discovered yet")
def _no_dealers_dialog() -> None:
    st.markdown(
        "Your search criteria have zip codes but no dealers have been discovered yet. "
        "Go to **🏪 Dealers** to find local dealerships — it only takes 1 API call per make."
    )
    col_go, col_cancel = st.columns(2)
    with col_go:
        if st.button("Go to 🏪 Dealers", type="primary", use_container_width=True):
            st.session_state["nav_page"] = "dealers"
            st.rerun()
    with col_cancel:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


def render() -> None:
    section_header("Recent Matches", "Listings that matched your saved criteria")

    has_criteria = len(load_criteria()) > 0
    settings = load_settings()

    # --- Search controls row ---
    col_btn, col_sched = st.columns([2, 3])

    with col_btn:
        if not has_criteria:
            st.button("🔍 Run Search Now", type="primary", use_container_width=True, disabled=True)
            st.caption("Add search criteria before running a search.")
        else:
            estimate = estimate_search_calls()
            no_dealers = (
                not settings.mock_mode
                and estimate["total_dealers"] == 0
                and len(estimate.get("warnings", [])) > 0
            )

            if st.button("🔍 Run Search Now", type="primary", use_container_width=True):
                if no_dealers:
                    _no_dealers_dialog()
                else:
                    progress_bar = st.progress(0, text="Starting search...")

                    def _on_progress(completed: int, total: int, label: str) -> None:
                        pct = completed / total if total else 1.0
                        progress_bar.progress(
                            pct,
                            text=f"Fetching dealer {completed}/{total} · {label}",
                        )

                    new_count, errors, used_mock = run_search(progress_cb=_on_progress)
                    progress_bar.empty()
                    record_manual_run()

                    for err in errors:
                        status_indicator("error", err)

                    if used_mock:
                        st.info("Mock mode is on — results are simulated. Disable it in ⚙️ Settings to search live listings.")

                    if new_count > 0:
                        all_matches = load_matches()
                        new_matches = [m for m in all_matches if not m.notified]
                        send_pushover(new_matches)
                        for m in all_matches:
                            m.notified = True
                        save_matches(all_matches)
                        status_indicator("success", f"{new_count} new match{'es' if new_count > 1 else ''} found!")
                        st.rerun()
                    elif not errors:
                        status_indicator("warning", "No new matches found.")

            _render_search_estimate(estimate)

    with col_sched:
        schedule_widget(has_criteria=has_criteria)

    # Compact API usage indicator — only shown when mock mode is off
    if not settings.mock_mode:
        acct = fetch_account_info()
        if acct:
            used = acct.get("this_month_usage", 0)
            total = acct.get("searches_per_month", 250)
            left = acct.get("plan_searches_left", total - used)
            pct = used / total if total else 0
            color = "#F44336" if pct >= 0.90 else "#FFC107" if pct >= 0.70 else "#009688"
            st.markdown(
                f"<p style='font-size:0.8rem;color:#757575;margin:4px 0 12px'>"
                f"API quota: <b style='color:{color}'>{used}/{total}</b> calls used · {left} remaining</p>",
                unsafe_allow_html=True,
            )

    st.markdown("")

    # --- Results ---
    matches = load_matches()
    mark_all_read()

    if not matches:
        empty_state(
            "No matches yet.",
            "Add search criteria then click Run Search Now.",
        )
        return

    result_col, clear_col = st.columns([6, 1])
    with result_col:
        st.markdown(f"**{len(matches)} result{'s' if len(matches) != 1 else ''}**")
    with clear_col:
        if st.button("Clear All", use_container_width=True):
            save_matches([])
            st.rerun()

    matches_sorted = sorted(matches, key=lambda m: m.found_at, reverse=True)
    for m in matches_sorted:
        match_card(m)


def _render_search_estimate(estimate: dict) -> None:
    if estimate.get("mock"):
        st.caption("Mock mode — 0 API calls")
        return

    live = estimate["live_calls"]
    cached = estimate["cached"]
    total = estimate["total_dealers"]
    groups = estimate.get("groups", [])
    warnings = estimate.get("warnings", [])

    if total == 0 and not warnings:
        st.caption("No dealers configured — go to 🏪 Dealers to discover them.")
        return

    parts: list[str] = []
    for g in groups:
        n = len(g["dealers"])
        if n:
            parts.append(f"{g['make']} {g['model']} × {n} dealer{'s' if n != 1 else ''}")

    if parts:
        live_calls = live * 2  # site: + platform search per dealer
        live_str = f"**{live_calls}** live call{'s' if live_calls != 1 else ''}" if live else ""
        cached_str = f"{cached * 2} cached" if cached else ""
        call_summary = " + ".join(filter(None, [live_str, cached_str])) or "0 calls"
        detail = ", ".join(parts)
        st.caption(f"{call_summary} · {detail} · 2 searches/dealer (site + platforms)")

    for w in warnings:
        st.caption(f"⚠ {w}")
