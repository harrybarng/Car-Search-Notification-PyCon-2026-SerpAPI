import streamlit as st


def badge(count: int) -> str:
    """Return an HTML teal badge string for embedding in markdown."""
    if count <= 0:
        return ""
    return (
        f"<span style='"
        f"background:#009688;color:#fff;border-radius:12px;"
        f"padding:1px 8px;font-size:0.75rem;font-weight:700;"
        f"vertical-align:middle;margin-left:6px'>"
        f"{count}"
        f"</span>"
    )
