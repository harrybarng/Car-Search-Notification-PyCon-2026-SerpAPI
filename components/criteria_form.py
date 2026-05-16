from __future__ import annotations

from datetime import datetime
from typing import Optional

import streamlit as st

from services.models import Criterion


def criteria_form(existing: Optional[Criterion] = None) -> Optional[Criterion]:
    """
    Renders the add/edit form for a criterion.
    Returns a Criterion if submitted, or None if cancelled.
    """
    c = existing
    is_edit = c is not None

    with st.form(key="criteria_form", clear_on_submit=True):
        st.markdown("#### " + ("Edit Criterion" if is_edit else "Add Criterion"))

        col1, col2 = st.columns(2)
        with col1:
            make = st.text_input("Make *", value=c.make if c else "").strip()
        with col2:
            model = st.text_input("Model *", value=c.model if c else "").strip()

        trim = st.text_input("Trim Level (optional)", value=c.trim or "" if c else "").strip()

        st.markdown("**Price Range (USD)**")
        pc1, pc2 = st.columns(2)
        with pc1:
            price_min = st.number_input("Min Price", min_value=0, value=c.price_min or 0 if c else 0, step=500)
        with pc2:
            price_max = st.number_input("Max Price", min_value=0, value=c.price_max or 0 if c else 0, step=500)

        st.markdown("**Year Range**")
        yc1, yc2 = st.columns(2)
        current_year = datetime.now().year
        with yc1:
            year_min = st.number_input("Min Year", min_value=1980, max_value=current_year + 1,
                                       value=c.year_min or 2015 if c else 2015)
        with yc2:
            year_max = st.number_input("Max Year", min_value=1980, max_value=current_year + 1,
                                       value=c.year_max or current_year if c else current_year)

        st.markdown("**Mileage Range**")
        mc1, mc2 = st.columns(2)
        with mc1:
            mileage_min = st.number_input("Min Mileage", min_value=0,
                                          value=c.mileage_min or 0 if c else 0, step=1000)
        with mc2:
            mileage_max = st.number_input("Max Mileage", min_value=0,
                                          value=c.mileage_max or 100000 if c else 100000, step=1000)

        st.markdown("**Location (optional)**")
        lc1, lc2 = st.columns(2)
        with lc1:
            zip_code = st.text_input(
                "Zip Code",
                value=c.zip_code or "" if c else "",
                placeholder="e.g. 90210",
                help="Center point for the search. Leave blank to search nationally.",
            ).strip()
        with lc2:
            radius_miles = st.number_input(
                "Radius (miles)",
                min_value=10,
                max_value=500,
                value=c.radius_miles or 50 if c else 50,
                step=10,
                help="Search within this distance from the zip code.",
            )

        col_save, col_cancel = st.columns([1, 1])
        submitted = col_save.form_submit_button("Save", type="primary", use_container_width=True)
        cancelled = col_cancel.form_submit_button("Cancel", use_container_width=True)

    if cancelled:
        return None

    if submitted:
        if not make or not model:
            st.error("Make and Model are required.")
            return None

        if zip_code and (not zip_code.isdigit() or len(zip_code) != 5):
            st.error("Zip code must be a 5-digit number.")
            return None

        now = datetime.utcnow()
        return Criterion(
            id=c.id if c else __import__("uuid").uuid4().__str__(),
            make=make,
            model=model,
            trim=trim or None,
            price_min=price_min if price_min > 0 else None,
            price_max=price_max if price_max > 0 else None,
            year_min=int(year_min),
            year_max=int(year_max),
            mileage_min=mileage_min if mileage_min > 0 else None,
            mileage_max=mileage_max if mileage_max > 0 else None,
            zip_code=zip_code or None,
            radius_miles=int(radius_miles),
            created_at=c.created_at if c else now,
            updated_at=now,
        )

    return None
