"""Application configuration management.

Handles API tokens, paths, and other settings with support for
environment variables and .env files.
"""

import json
import os
from pathlib import Path
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


class Config:  # noqa: PLR0904
    """Application configuration."""

    # Base paths (Constant)
    PROJECT_ROOT: Path = Path(__file__).parent.parent

    # Default paths (Fallback if session not initialized)
    DEFAULT_DATA_DIR: Path = PROJECT_ROOT / "data"
    DEFAULT_PHOTOS_DIR: Path = DEFAULT_DATA_DIR / "photos"
    DEFAULT_CACHE_DIR: Path = DEFAULT_DATA_DIR / "cache"
    DEFAULT_EXPORTS_DIR: Path = PROJECT_ROOT / "exports"

    # Files
    DEFAULT_RECEIPTS_CSV: Path = DEFAULT_DATA_DIR / "receipts.csv"
    DEFAULT_ITEMS_CSV: Path = DEFAULT_DATA_DIR / "items.csv"
    DEFAULT_CACHE_FILE: Path = DEFAULT_CACHE_DIR / "processed.json"
    CATEGORIES_FILE: Path = DEFAULT_DATA_DIR / "categories.json"

    # Dynamic Category Definitions (Loaded on demand)
    _CATEGORIES: dict = {}

    # Defaults
    DEFAULT_GEMINI_MODEL: str = "gemini-2.0-flash"
    DEFAULT_HF_MODEL: str = "Qwen/Qwen2-VL-7B-Instruct"
    MAX_IMAGE_SIZE: int = int(os.getenv("MAX_IMAGE_SIZE", "2048"))
    SUPPORTED_IMAGE_EXTENSIONS: tuple = (".jpg", ".jpeg", ".png", ".heic", ".heif")
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "JPY")

    @classmethod
    def get_data_dir(cls) -> Path:
        """Get data directory for the current session."""
        if hasattr(st, "session_state") and "data_dir" in st.session_state:
            return Path(st.session_state.data_dir)
        return cls.DEFAULT_DATA_DIR

    @classmethod
    def get_photos_dir(cls) -> Path:
        """Get photos directory for the current session."""
        if hasattr(st, "session_state") and "photos_dir" in st.session_state:
            return Path(st.session_state.photos_dir)
        return cls.DEFAULT_PHOTOS_DIR

    @classmethod
    def get_cache_dir(cls) -> Path:
        """Get cache directory for the current session."""
        if hasattr(st, "session_state") and "cache_dir" in st.session_state:
            return Path(st.session_state.cache_dir)
        return cls.DEFAULT_CACHE_DIR

    @classmethod
    def get_exports_dir(cls) -> Path:
        """Get exports directory. defaults to project exports to be retrievable."""
        # Exports could be session specific too, but maybe user wants to download them?
        # Streamlit handles downloads via buffer usually.
        # Let's keep strict isolation.
        if hasattr(st, "session_state") and "exports_dir" in st.session_state:
            return Path(st.session_state.exports_dir)
        return cls.DEFAULT_EXPORTS_DIR

    @classmethod
    def get_receipts_csv(cls) -> Path:
        return cls.get_data_dir() / "receipts.csv"

    @classmethod
    def get_items_csv(cls) -> Path:
        return cls.get_data_dir() / "items.csv"

    @classmethod
    def get_cache_file(cls) -> Path:
        return cls.get_cache_dir() / "processed.json"

    # --- API Configuration ---

    @classmethod
    def get_gemini_api_key(cls) -> Optional[str]:
        """Get Gemini API key from session state or env."""
        # 1. Session state (User input)
        if hasattr(st, "session_state") and st.session_state.get("gemini_api_key"):
            return st.session_state.gemini_api_key
        # 2. Environment variable (Deployment config)
        return os.getenv("GEMINI_API_KEY")

    @classmethod
    def get_hf_token(cls) -> Optional[str]:
        """Get Hugging Face token from session state or env."""
        if hasattr(st, "session_state") and st.session_state.get("hf_token"):
            return st.session_state.hf_token
        return os.getenv("HUGGINGFACE_TOKEN")

    @classmethod
    def get_maps_api_key(cls) -> Optional[str]:
        """Get Google Maps API key."""
        if hasattr(st, "session_state") and st.session_state.get("maps_api_key"):
            return st.session_state.maps_api_key
        return os.getenv("GOOGLE_MAPS_API_KEY")

    @classmethod
    def get_provider(cls) -> str:
        """Get current extraction provider."""
        if hasattr(st, "session_state") and st.session_state.get("extraction_provider"):
            return st.session_state.extraction_provider
        return os.getenv("EXTRACTION_PROVIDER", "gemini")

    @classmethod
    def get_gemini_model(cls) -> str:
        if hasattr(st, "session_state") and st.session_state.get("gemini_model"):
            return st.session_state.gemini_model
        return os.getenv("GEMINI_MODEL", cls.DEFAULT_GEMINI_MODEL)

    @classmethod
    def get_hf_model(cls) -> str:
        if hasattr(st, "session_state") and st.session_state.get("hf_model"):
            return st.session_state.hf_model
        return os.getenv("HUGGINGFACE_MODEL", cls.DEFAULT_HF_MODEL)

    # --- Language Settings ---

    @classmethod
    def get_primary_language(cls) -> str:
        if hasattr(st, "session_state") and st.session_state.get("primary_language"):
            return st.session_state.primary_language
        return os.getenv("PRIMARY_LANGUAGE", "Traditional Chinese")

    @classmethod
    def get_destination_language(cls) -> str:
        if hasattr(st, "session_state") and st.session_state.get("destination_language"):
            return st.session_state.destination_language
        return os.getenv("DESTINATION_LANGUAGE", "Japanese")

    # --- State Setters (Helpers) ---

    @classmethod
    def set_gemini_api_key(cls, key: str) -> None:
        st.session_state.gemini_api_key = key

    @classmethod
    def set_hf_token(cls, token: str) -> None:
        st.session_state.hf_token = token

    @classmethod
    def set_provider(cls, provider: str) -> None:
        st.session_state.extraction_provider = provider

    @classmethod
    def set_language_settings(cls, primary: str, dest: str) -> None:
        st.session_state.primary_language = primary
        st.session_state.destination_language = dest

    @classmethod
    def set_gemini_model(cls, model: str) -> None:
        st.session_state.gemini_model = model

    @classmethod
    def set_huggingface_model(cls, model: str) -> None:
        st.session_state.hf_model = model

    # --- Categories ---

    @classmethod
    def get_categories(cls) -> dict:
        """Get categories. Load from file if not loaded."""
        # Try session specific categories first
        if hasattr(st, "session_state") and st.session_state.get("categories"):
            return st.session_state.categories

        # Fallback to loading from default file if session not ready or empty
        if not cls._CATEGORIES:
            cls.load_default_categories()
        return cls._CATEGORIES

    @classmethod
    def load_default_categories(cls) -> None:
        """Load categories from default JSON file."""
        if cls.CATEGORIES_FILE.exists():
            try:
                with open(cls.CATEGORIES_FILE, encoding="utf-8") as f:
                    cls._CATEGORIES = json.load(f)
            except Exception:
                pass

    @classmethod
    def save_categories(cls, categories: dict) -> None:
        """Save categories to session state."""
        # For security, we only save to session state in this mode
        if hasattr(st, "session_state"):
            st.session_state.categories = categories

            # Start: Also save to disk?
            # In session isolation mode, users shouldn't modify the GLOBAL defaults.
            # So we DO NOT save to cls.CATEGORIES_FILE.
            # We save to the session's data dir.
            session_cat_file = cls.get_data_dir() / "categories.json"
            try:
                with open(session_cat_file, "w", encoding="utf-8") as f:
                    json.dump(categories, f, ensure_ascii=False, indent=4)
            except Exception:
                pass

    @classmethod
    def get_category_emoji(cls, category: str) -> str:
        return cls.get_categories().get(category, {}).get("emoji", "📦")

    @classmethod
    def get_category_label(cls, category: str) -> str:
        return cls.get_categories().get(category, {}).get("label", "其他")

    @classmethod
    def get_subcategories(cls, category: str) -> list[str]:
        return cls.get_categories().get(category, {}).get("subcategories", [])

    # --- Directory Management ---

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure all required directories exist."""
        # This acts on the currently active directories (session or default)
        cls.get_data_dir().mkdir(parents=True, exist_ok=True)
        cls.get_photos_dir().mkdir(parents=True, exist_ok=True)
        cls.get_cache_dir().mkdir(parents=True, exist_ok=True)
        cls.get_exports_dir().mkdir(parents=True, exist_ok=True)

    # --- Status Checks ---

    @classmethod
    def is_gemini_configured(cls) -> bool:
        key = cls.get_gemini_api_key()
        return key is not None and len(key) > 0

    @classmethod
    def is_hf_configured(cls) -> bool:
        token = cls.get_hf_token()
        return token is not None and len(token) > 0

    @classmethod
    def is_current_provider_configured(cls) -> bool:
        if cls.get_provider() == "huggingface":
            return cls.is_hf_configured()
        return cls.is_gemini_configured()

    @classmethod
    def get_provider_display_name(cls) -> str:
        if cls.get_provider() == "huggingface":
            return f"Hugging Face ({cls.get_hf_model()})"
        return f"Google Gemini ({cls.get_gemini_model()})"
