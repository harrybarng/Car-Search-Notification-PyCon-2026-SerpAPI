from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # loads .env into os.environ before anything else runs

import streamlit as st

# --- Logging setup (runs once at import time) ---
_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_handler = logging.handlers.RotatingFileHandler(
    _LOG_DIR / "app.log", maxBytes=1_000_000, backupCount=3
)
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])

# --- Page config (must be first Streamlit call) ---
st.set_page_config(
    page_title="Car Search Alerts",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Ensure data directory and files exist (safe for fresh clones) ---
from services.storage import ensure_data_files
ensure_data_files()

# --- Start background scheduler once per process ---
if "scheduler_started" not in st.session_state:
    from services.scheduler import start_scheduler
    start_scheduler()
    st.session_state["scheduler_started"] = True

# --- Sidebar navigation ---
from services.storage import unread_count

count = unread_count()

with st.sidebar:
    st.markdown("## 🚗 Car Alerts")
    st.markdown("---")

    home_label = f"🏠 Home ({count})" if count > 0 else "🏠 Home"

    def _nav_label(x: str) -> str:
        if x == "home":
            return home_label
        if x == "criteria":
            return "🔍 Search Criteria"
        if x == "dealers":
            return "🏪 Dealers"
        return "⚙️ Settings"

    page = st.radio(
        "Navigate",
        options=["home", "criteria", "dealers", "settings"],
        format_func=_nav_label,
        label_visibility="collapsed",
        key="nav_page",
    )

# --- Render selected page ---
if page == "home":
    from views.home import render
    render()
elif page == "criteria":
    from views.criteria import render
    render()
elif page == "dealers":
    from views.dealers import render
    render()
else:
    from views.settings import render
    render()
