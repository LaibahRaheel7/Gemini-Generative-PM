"""
User identity and per-user state file paths.
Uses Hugging Face OAuth (st.user) when available; otherwise a session-scoped guest id.
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
    """
    Stable user id for the current session.
    Prefers Hugging Face OAuth (st.user.sub or preferred_username); else session guest id.
    """
    import streamlit as st

    # HF OAuth / Streamlit auth: st.user is dict-like with is_logged_in
    user = getattr(st, "user", None)
    if user is not None and getattr(user, "is_logged_in", False):
        for key in ("sub", "preferred_username", "name", "email"):
            raw = user.get(key) if hasattr(user, "get") and callable(user.get) else getattr(user, key, None)
            if raw:
                return _sanitize_user_id(str(raw))

    # Guest / local: one id per browser session
    if "_guest_user_id" not in st.session_state:
        st.session_state._guest_user_id = f"guest_{uuid.uuid4().hex[:12]}"
    return st.session_state._guest_user_id


def get_state_path(user_id: Optional[str] = None) -> str:
    """Path to the state JSON file for the given user (default: current user)."""
    uid = user_id if user_id is not None else get_user_id()
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    return os.path.join(USER_DATA_DIR, f"state_{_sanitize_user_id(uid)}.json")


def is_logged_in_via_provider() -> bool:
    """True if the current user is identified via OAuth (e.g. HF login)."""
    import streamlit as st

    user = getattr(st, "user", None)
    if user is None:
        return False
    return getattr(user, "is_logged_in", False)
