"""Application configuration management.

Handles API tokens, paths, and other settings with support for
environment variables and .env files.
"""

import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    # Base paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    PHOTOS_DIR: Path = DATA_DIR / "photos"
    CACHE_DIR: Path = DATA_DIR / "cache"
    EXPORTS_DIR: Path = PROJECT_ROOT / "exports"

    # Data files
    RECEIPTS_CSV: Path = DATA_DIR / "receipts.csv"
    ITEMS_CSV: Path = DATA_DIR / "items.csv"
    CACHE_FILE: Path = CACHE_DIR / "processed.json"

    # API Configuration
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Google Maps for geocoding
    GOOGLE_MAPS_API_KEY: Optional[str] = os.getenv("GOOGLE_MAPS_API_KEY")

    # Processing settings
    MAX_IMAGE_SIZE: int = int(os.getenv("MAX_IMAGE_SIZE", "2048"))
    SUPPORTED_IMAGE_EXTENSIONS: tuple = (".jpg", ".jpeg", ".png", ".heic", ".heif")

    # Default currency
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "JPY")
    # Language settings
    PRIMARY_LANGUAGE: str = os.getenv("PRIMARY_LANGUAGE", "Traditional Chinese")
    DESTINATION_LANGUAGE: str = os.getenv("DESTINATION_LANGUAGE", "Japanese")

    # Category definitions
    CATEGORIES_FILE: Path = DATA_DIR / "categories.json"

    # Category definitions (Dynamic)
    CATEGORIES: dict = {}

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure all required directories exist."""
        cls.PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cls.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # Load categories
        if cls.CATEGORIES_FILE.exists():
            try:
                with open(cls.CATEGORIES_FILE, encoding="utf-8") as f:
                    cls.CATEGORIES = json.load(f)
            except Exception:
                # Fallback or empty, but usually file should exist
                pass
        else:
            # Create default if not exists (although we just created it)
            pass

    @classmethod
    def save_categories(cls, categories: dict) -> None:
        """Save categories to JSON file."""
        cls.CATEGORIES = categories
        with open(cls.CATEGORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(categories, f, ensure_ascii=False, indent=4)

    @classmethod
    def is_gemini_configured(cls) -> bool:
        """Check if Gemini API is properly configured."""
        return cls.GEMINI_API_KEY is not None and len(cls.GEMINI_API_KEY) > 0

    @classmethod
    def is_maps_configured(cls) -> bool:
        """Check if Google Maps API is properly configured."""
        return cls.GOOGLE_MAPS_API_KEY is not None and len(cls.GOOGLE_MAPS_API_KEY) > 0

    @classmethod
    def set_gemini_api_key(cls, api_key: str) -> None:
        """Set Gemini API key at runtime (e.g., from Streamlit UI)."""
        cls.GEMINI_API_KEY = api_key
        os.environ["GEMINI_API_KEY"] = api_key

    @classmethod
    def set_google_maps_api_key(cls, api_key: str) -> None:
        """Set Google Maps API key at runtime."""
        cls.GOOGLE_MAPS_API_KEY = api_key
        os.environ["GOOGLE_MAPS_API_KEY"] = api_key

    @classmethod
    def set_language_settings(cls, primary: str, destination: str) -> None:
        """Set language settings."""
        cls.PRIMARY_LANGUAGE = primary
        cls.DESTINATION_LANGUAGE = destination
        os.environ["PRIMARY_LANGUAGE"] = primary
        os.environ["DESTINATION_LANGUAGE"] = destination

    @classmethod
    def get_category_emoji(cls, category: str) -> str:
        """Get emoji for a category."""
        return cls.CATEGORIES.get(category, {}).get("emoji", "📦")

    @classmethod
    def get_category_label(cls, category: str) -> str:
        """Get label for a category."""
        return cls.CATEGORIES.get(category, {}).get("label", "其他")

    @classmethod
    def get_subcategories(cls, category: str) -> list[str]:
        """Get subcategories for a category."""
        return cls.CATEGORIES.get(category, {}).get("subcategories", [])


# Initialize directories on import
Config.ensure_directories()
