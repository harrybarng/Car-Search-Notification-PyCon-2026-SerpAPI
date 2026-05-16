from __future__ import annotations

import os
from datetime import datetime

import streamlit as st

from components.empty_state import empty_state
from components.section_header import section_header
from components.status_indicator import status_indicator
from services.dealers import discover_dealers, load_all, load_dealers, remove_entry, save_dealers
from services.storage import load_criteria


def render() -> None:
    section_header("Dealers", "Discover and manage local dealerships by zip code")

    serp_key = os.environ.get("SERPAPI_KEY", "")
    criteria = load_criteria()

    # Collect unique (zip, make) pairs from criteria that have a zip code
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for c in criteria:
        if c.zip_code:
            key = (c.zip_code, c.make)
            if key not in seen:
                seen.add(key)
                pairs.append(key)

    if not pairs:
        empty_state(
            "No zip codes configured.",
            "Add a zip code to at least one search criterion to enable dealer discovery.",
        )
        return

    if not serp_key:
        st.warning(
            "SERPAPI_KEY is not set. Set it in your .env file to run dealer discovery.",
            icon="⚠️",
        )

    all_stored = load_all()

    for zip_code, make in pairs:
        entry_key = f"{zip_code}_{make.lower()}"
        entry = all_stored.get(entry_key, {})
        dealers = [d for d in [
            _safe_dealer(d) for d in entry.get("dealers", [])
        ] if d]
        discovered_at: str | None = entry.get("discovered_at")

        st.markdown(f"### {make} dealers near {zip_code}")

        col_info, col_btn = st.columns([4, 2])
        with col_info:
            if discovered_at:
                try:
                    dt = datetime.fromisoformat(discovered_at)
                    st.caption(f"Last discovered: {dt.strftime('%b %d, %Y at %H:%M UTC')} · {len(dealers)} dealer(s) found")
                except Exception:
                    st.caption(f"{len(dealers)} dealer(s) stored")
            else:
                st.caption("Not yet discovered.")

        with col_btn:
            btn_key = f"discover_{zip_code}_{make}"
            disabled = not serp_key
            if st.button(
                f"Discover {make} Dealers",
                key=btn_key,
                use_container_width=True,
                disabled=disabled,
                type="primary" if not dealers else "secondary",
            ):
                with st.spinner(f"Searching for {make} dealers near {zip_code}..."):
                    new_dealers, error = discover_dealers(zip_code, make, serp_key)
                if error:
                    status_indicator("error", error)
                else:
                    save_dealers(zip_code, make, new_dealers)
                    status_indicator("success", f"Found {len(new_dealers)} {make} dealer(s) near {zip_code}.")
                    st.rerun()

        if dealers:
            for dealer in dealers:
                with st.container():
                    d_col1, d_col2, d_col3 = st.columns([3, 3, 1])
                    with d_col1:
                        rating_str = f" ⭐ {dealer['rating']}" if dealer.get("rating") else ""
                        st.markdown(f"**{dealer['name']}**{rating_str}")
                        st.caption(dealer.get("address", ""))
                    with d_col2:
                        st.caption(f"`{dealer['domain']}`")
                        if dealer.get("phone"):
                            st.caption(dealer["phone"])
                    with d_col3:
                        if st.button("Remove", key=f"rm_{zip_code}_{make}_{dealer['domain']}", use_container_width=True):
                            stored = load_dealers(zip_code, make)
                            updated = [d for d in stored if d.domain != dealer["domain"]]
                            save_dealers(zip_code, make, updated)
                            st.rerun()
                st.markdown(
                    "<hr style='margin:4px 0;border-color:#E0E0E0'>",
                    unsafe_allow_html=True,
                )
        else:
            st.info(f"No dealers stored yet. Click **Discover {make} Dealers** to search.")

        st.markdown("")

    st.markdown("---")
    st.caption(
        "Dealer discovery uses 1 SerpAPI call per (zip, make) pair. "
        "Results are stored permanently and only refreshed when you click Discover again."
    )


def _safe_dealer(raw: dict) -> dict | None:
    try:
        return raw if raw.get("domain") else None
    except Exception:
        return None
