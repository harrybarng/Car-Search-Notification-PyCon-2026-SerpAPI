from __future__ import annotations

import streamlit as st

from services.models import Schedule
from services.storage import load_schedule, save_schedule
from services.scheduler import refresh_schedule


def schedule_widget(has_criteria: bool = True) -> None:
    """Inline schedule configuration row shown on the Home page."""
    schedule = load_schedule()

    with st.expander("⏰ Schedule", expanded=False):
        if not has_criteria:
            st.caption("⚠️ Add search criteria before enabling a schedule.")

        enabled = st.toggle(
            "Enable daily scheduled search",
            value=schedule.enabled,
            disabled=not has_criteria,
        )

        col1, col2 = st.columns(2)
        with col1:
            run_at = st.text_input(
                "Run at (HH:MM, 24h)",
                value=schedule.run_at,
                disabled=not enabled or not has_criteria,
                help="Time in 24-hour format, e.g. 08:00",
            )
        with col2:
            buffer_hours = st.number_input(
                "Skip if searched within (hours)",
                min_value=0,
                max_value=24,
                value=schedule.buffer_hours,
                disabled=not enabled or not has_criteria,
                help="If you run a manual search within this many hours of the scheduled time, the scheduled run is skipped.",
            )

        if schedule.last_run_at:
            st.caption(f"Last run: {schedule.last_run_at.strftime('%b %d, %Y at %I:%M %p UTC')}")

        if st.button("Save Schedule", type="primary", disabled=not has_criteria or (not enabled and not schedule.enabled)):
            try:
                hour, minute = run_at.strip().split(":")
                assert 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59
            except (ValueError, AssertionError):
                st.error("Invalid time format. Use HH:MM (e.g. 08:00).")
                return

            updated = Schedule(
                enabled=enabled,
                run_at=run_at.strip(),
                buffer_hours=int(buffer_hours),
                last_run_at=schedule.last_run_at,
            )
            save_schedule(updated)
            refresh_schedule()
            st.success("Schedule saved.")
            st.rerun()
