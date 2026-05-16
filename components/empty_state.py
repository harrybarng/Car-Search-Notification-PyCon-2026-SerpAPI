import streamlit as st


def empty_state(message: str, hint: str = "") -> None:
    st.markdown(
        f"""
        <div style="
            background:#F5F5F5;
            border:1px solid #E0E0E0;
            border-radius:8px;
            padding:40px 24px;
            text-align:center;
            color:#757575;
        ">
            <p style="font-size:1.1rem;margin:0">{message}</p>
            {"<p style='font-size:0.9rem;margin:8px 0 0'>" + hint + "</p>" if hint else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )
