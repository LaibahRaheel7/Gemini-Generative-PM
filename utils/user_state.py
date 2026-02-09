"""
Per-session state file paths. Each browser session gets its own state file.
"""
import os
import re
import uuid
from typing import Optional

# Directory for per-user state files (created on first use)
USER_DATA_DIR = "user_data"


def _sanitize_user_id(raw: str) -> str:
    """Safe filename segment from user id (alphanumeric + underscore)."""
    if not raw:
        return "anonymous"
    safe = re.sub(r"[^\w\-]", "_", str(raw).strip())[:64]
    return safe or "anonymous"


def get_user_id() -> str:
    """Stable session id: one id per browser session (guest_xxxx)."""
    import streamlit as st

    if "_guest_user_id" not in st.session_state:
        st.session_state._guest_user_id = f"guest_{uuid.uuid4().hex[:12]}"
    return st.session_state._guest_user_id


def get_state_path(user_id: Optional[str] = None) -> str:
    """Path to the state JSON file for the given user (default: current session)."""
    uid = user_id if user_id is not None else get_user_id()
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    return os.path.join(USER_DATA_DIR, f"state_{_sanitize_user_id(uid)}.json")
