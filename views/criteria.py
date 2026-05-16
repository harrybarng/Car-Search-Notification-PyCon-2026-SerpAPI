from __future__ import annotations

import streamlit as st

from components.criteria_card import criteria_card
from components.criteria_form import criteria_form
from components.empty_state import empty_state
from components.section_header import section_header
from services.models import Criterion
from services.storage import add_criterion, delete_criterion, load_criteria, update_criterion


def render() -> None:
    section_header("Search Criteria", "Define what cars you're looking for")

    # Session state for form visibility and editing
    if "show_form" not in st.session_state:
        st.session_state.show_form = False
    if "editing_criterion" not in st.session_state:
        st.session_state.editing_criterion = None

    def open_add() -> None:
        st.session_state.show_form = True
        st.session_state.editing_criterion = None

    def open_edit(c: Criterion) -> None:
        st.session_state.show_form = True
        st.session_state.editing_criterion = c

    def handle_delete(criterion_id: str) -> None:
        delete_criterion(criterion_id)
        st.rerun()

    if not st.session_state.show_form:
        if st.button("+ Add Criteria", type="primary"):
            open_add()
            st.rerun()

    if st.session_state.show_form:
        result = criteria_form(existing=st.session_state.editing_criterion)
        if result is not None:
            if st.session_state.editing_criterion:
                update_criterion(result)
            else:
                add_criterion(result)
            st.session_state.show_form = False
            st.session_state.editing_criterion = None
            st.rerun()

        if st.button("Cancel", key="cancel_form"):
            st.session_state.show_form = False
            st.session_state.editing_criterion = None
            st.rerun()

    st.markdown("")

    criteria = load_criteria()
    if not criteria:
        empty_state(
            "No criteria saved yet.",
            "Click '+ Add Criteria' to define your first car search.",
        )
        return

    for c in criteria:
        criteria_card(c, on_edit=open_edit, on_delete=handle_delete)
