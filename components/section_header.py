import streamlit as st


def section_header(title: str, subtitle: str = "") -> None:
    st.markdown(f"## {title}")
    if subtitle:
        st.markdown(f"<p style='color:#757575;margin-top:-12px'>{subtitle}</p>", unsafe_allow_html=True)
    st.markdown("---")
