import streamlit as st
from services.models import Criterion


def _fmt_range(lo: int | None, hi: int | None, prefix: str = "", suffix: str = "") -> str:
    if lo is None and hi is None:
        return "Any"
    if lo is not None and hi is not None:
        return f"{prefix}{lo:,}{suffix} – {prefix}{hi:,}{suffix}"
    if lo is not None:
        return f"≥ {prefix}{lo:,}{suffix}"
    return f"≤ {prefix}{hi:,}{suffix}"


def criteria_card(criterion: Criterion, on_edit: callable, on_delete: callable) -> None:
    trim_html = (
        f"&nbsp;<span style='font-size:0.9rem;font-weight:400;color:#757575'>{criterion.trim}</span>"
        if criterion.trim else ""
    )
    location_html = (
        f"<span><b>Location:</b> {criterion.zip_code} ({criterion.radius_miles} mi radius)</span>"
        if criterion.zip_code else ""
    )
    with st.container():
        st.markdown(
            f"""
            <div style="background:#F5F5F5;border:1px solid #E0E0E0;border-radius:8px;padding:16px 20px;margin-bottom:4px;">
                <div style="font-size:1.05rem;font-weight:700;color:#212121">
                    {criterion.make} {criterion.model}{trim_html}
                </div>
                <div style="margin-top:8px;display:flex;gap:24px;flex-wrap:wrap;font-size:0.875rem;color:#757575">
                    <span><b>Price:</b> {_fmt_range(criterion.price_min, criterion.price_max, "$")}</span>
                    <span><b>Year:</b> {_fmt_range(criterion.year_min, criterion.year_max)}</span>
                    <span><b>Miles:</b> {_fmt_range(criterion.mileage_min, criterion.mileage_max, suffix=" mi")}</span>
                    {location_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, _ = st.columns([1, 1, 8])
        with col1:
            if st.button("Edit", key=f"edit_{criterion.id}"):
                on_edit(criterion)
        with col2:
            if st.button("Delete", key=f"del_{criterion.id}", type="secondary"):
                on_delete(criterion.id)
