"""Session management utilities."""

import os
import shutil
import tempfile
from pathlib import Path

import streamlit as st
from loguru import logger

from src.config import Config


def init_session():
    """Initialize session state and temporary directories."""
    if "session_id" not in st.session_state:
        # Create temporary directory for this session
        temp_dir = tempfile.mkdtemp(prefix="trip_ledger_")
        st.session_state.session_id = os.path.basename(temp_dir)

        # Set paths in session state
        st.session_state.data_dir = str(Path(temp_dir) / "data")
        st.session_state.photos_dir = str(Path(st.session_state.data_dir) / "photos")
        st.session_state.cache_dir = str(Path(st.session_state.data_dir) / "cache")
        st.session_state.exports_dir = str(Path(temp_dir) / "exports")

        # Create directories
        Config.ensure_directories()

        # Copy default categories if available
        # We need to copy it because categories might be edited (if allowed),
        # or just to have a consistent starting point.
        # But wait, Config.CATEGORIES_FILE points to session dir now (via get_data_dir).
        # We need to copy from PROJECT_ROOT/data/categories.json to session/data/categories.json

        default_categories = Config.PROJECT_ROOT / "data" / "categories.json"
        session_categories = Path(st.session_state.data_dir) / "categories.json"

        if default_categories.exists():
            try:
                shutil.copy2(default_categories, session_categories)
            except Exception:
                pass

        # Initialize other session variables if needed
        # (API keys are handled by Config getters returning None if not set)

        # Log initialization (optional, good for debugging)
        logger.info(f"Initialized session: {st.session_state.session_id} at {temp_dir}")


def cleanup_session():
    """Cleanup session temporary files."""
    # This is hard to trigger reliably in Streamlit.
    # We rely on OS temp cleanup or manual cleanup if we implement a button.
    pass
