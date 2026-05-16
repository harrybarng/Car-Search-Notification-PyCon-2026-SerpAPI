import streamlit as st
from datetime import datetime

from services.models import Match


def _fmt_currency(value: int | None) -> str:
    return f"${value:,}" if value is not None else "—"


def _fmt_mileage(value: int | None) -> str:
    return f"{value:,} mi" if value is not None else "—"


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%b %d, %Y at %I:%M %p UTC")


def match_card(match: Match) -> None:
    border_color = "#009688" if not match.read else "#E0E0E0"
    st.markdown(
        f"""
        <div style="
            background:#fff;
            border:1px solid {border_color};
            border-left:4px solid {border_color};
            border-radius:8px;
            padding:16px 20px;
            margin-bottom:12px;
        ">
            <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <div>
                    <span style="font-size:1.05rem;font-weight:700;color:#212121">
                        {match.year or '—'} {match.make} {match.model}
                    </span>
                    {"<span style='margin-left:8px;color:#757575;font-size:0.9rem'>" + (match.trim or '') + "</span>" if match.trim else ""}
                </div>
                <span style="font-size:1.1rem;font-weight:700;color:#009688">{_fmt_currency(match.price)}</span>
            </div>
            <div style="margin-top:8px;color:#757575;font-size:0.875rem">
                {_fmt_mileage(match.mileage)}
                &nbsp;·&nbsp;
                Found {_fmt_dt(match.found_at)}
                {"&nbsp;·&nbsp;" + match.source if match.source else ""}
            </div>
            <div style="margin-top:10px">
                <a href="{match.listing_url}" target="_blank"
                   style="color:#009688;font-weight:600;text-decoration:none;font-size:0.9rem">
                    View Listing →
                </a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
