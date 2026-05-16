import streamlit as st

_COLORS = {
    "success": "#4CAF50",
    "warning": "#FFC107",
    "error": "#F44336",
}


def status_indicator(state: str, message: str) -> None:
    """state must be 'success', 'warning', or 'error'."""
    color = _COLORS.get(state, "#757575")
    st.markdown(
        f"""
        <div style="
            display:flex;align-items:center;gap:8px;
            padding:10px 14px;
            border-radius:6px;
            background:{color}18;
            border-left:4px solid {color};
            margin-bottom:8px;
        ">
            <span style="color:{color};font-weight:600">{message}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
