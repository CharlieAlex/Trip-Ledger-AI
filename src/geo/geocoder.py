"""Geocoding service for converting addresses to coordinates.

Uses Google Maps Geocoding API with caching support.
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

from src.config import Config
from src.etl.models import GeoLocation
from src.etl.storage import ReceiptStorage


class GeocodingCache:
    """Cache for geocoding results."""

    def __init__(self, cache_file: Path | None = None):
        """Initialize cache.

        Args:
            cache_file: Path to cache file
        """
        self.cache_file = cache_file or (Config.CACHE_DIR / "geocoding.json")
        self._cache: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Load cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    self._cache = json.load(f)
            except (json.JSONDecodeError, Exception):
                self._cache = {}

    def _save(self) -> None:
        """Save cache to file."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def get(self, query: str) -> Optional[dict]:
        """Get cached result.

        Args:
            query: Geocoding query

        Returns:
            Cached result or None
        """
        return self._cache.get(query.lower())

    def set(self, query: str, result: dict) -> None:
        """Cache a result.

        Args:
            query: Geocoding query
            result: Geocoding result
        """
        self._cache[query.lower()] = result
        self._save()


class Geocoder:
    """Geocoding service using Google Maps API."""

    GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize geocoder.

        Args:
            api_key: Google Maps API key
        """
        self.api_key = api_key or Config.GOOGLE_MAPS_API_KEY
        self.cache = GeocodingCache()

    def geocode(
        self,
        query: str,
        region: str | None = None,
    ) -> Optional[GeoLocation]:
        """Convert address/name to coordinates.

        Args:
            query: Address or place name
            region: Region hint (e.g., "japan", "taiwan")

        Returns:
            GeoLocation or None if not found
        """
        if not query:
            return None

        # Check cache first
        cached = self.cache.get(query)
        if cached:
            return GeoLocation(**cached)

        # API call requires API key
        if not self.api_key:
            return None

        try:
            result = self._call_api(query, region)
            if result:
                self.cache.set(query, result)
                return GeoLocation(**result)
        except Exception as e:
            logger.error(f"Geocoding error: {e}")

        return None

    def _call_api(
        self,
        query: str,
        region: str | None = None,
    ) -> Optional[dict]:
        """Make API call to Google Maps Geocoding.

        Args:
            query: Search query
            region: Region bias

        Returns:
            Dict with location data or None
        """
        params = {
            "address": query,
            "key": self.api_key,
        }

        if region:
            # Map common region names to ccTLDs
            region_map = {
                "japan": "jp",
                "taiwan": "tw",
                "korea": "kr",
                "us": "us",
                "usa": "us",
            }
            params["region"] = region_map.get(region.lower(), region)

        url = f"{self.GEOCODING_URL}?{urllib.parse.urlencode(params)}"

        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())

        if data.get("status") != "OK" or not data.get("results"):
            return None

        result = data["results"][0]
        location = result["geometry"]["location"]

        return {
            "latitude": location["lat"],
            "longitude": location["lng"],
            "formatted_address": result.get("formatted_address"),
            "place_id": result.get("place_id"),
        }

    def geocode_receipts(self, data_dir: Path | None = None) -> int:
        """Batch update receipts with geocoding data.

        Args:
            data_dir: Directory containing receipts.csv

        Returns:
            Number of receipts updated
        """
        storage = ReceiptStorage(data_dir)
        df = storage.load_receipts()

        if len(df) == 0:
            return 0

        updated = 0
        for idx, row in df.iterrows():
            # Skip if already has coordinates
            if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
                continue

            # Try to geocode using store address or name
            query = row.get("store_address") or row.get("store_name")
            if not query:
                continue

            result = self.geocode(query, region="japan")
            if result:
                df.loc[idx, "latitude"] = result.latitude
                df.loc[idx, "longitude"] = result.longitude
                updated += 1

        if updated > 0:
            df.to_csv(storage.receipts_file, index=False)

        return updated


def geocode_address(
    query: str,
    region: str | None = None,
) -> Optional[GeoLocation]:
    """Convenience function for geocoding.

    Args:
        query: Address or place name
        region: Region hint

    Returns:
        GeoLocation or None
    """
    geocoder = Geocoder()
    return geocoder.geocode(query, region)
