"""Cache management for processed invoices.

Tracks processed images to avoid redundant API calls.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from src.config import Config
from src.etl.models import CacheEntry


class ProcessingCache:
    """Manage cache of processed invoice images."""

    def __init__(self, cache_file: Path | None = None):
        """Initialize cache.

        Args:
            cache_file: Path to cache file. Defaults to Config.CACHE_FILE
        """
        self.cache_file = cache_file or Config.get_cache_file()
        self._cache: dict[str, CacheEntry] = {}
        self._load()

    def _load(self) -> None:
        """Load cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                    for file_hash, entry_data in data.items():
                        self._cache[file_hash] = CacheEntry(**entry_data)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to load cache: {e}")
                self._cache = {}

    def _save(self) -> None:
        """Save cache to file."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            file_hash: entry.model_dump(mode="json")
            for file_hash, entry in self._cache.items()
        }
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def is_processed(self, file_hash: str) -> bool:
        """Check if an image has been processed.

        Args:
            file_hash: SHA256 hash of the image file

        Returns:
            True if image was successfully processed before
        """
        entry = self._cache.get(file_hash)
        return entry is not None and entry.status == "success"

    def get_entry(self, file_hash: str) -> Optional[CacheEntry]:
        """Get cache entry for a file hash.

        Args:
            file_hash: SHA256 hash of the image file

        Returns:
            CacheEntry if exists, None otherwise
        """
        return self._cache.get(file_hash)

    def add_success(
        self,
        file_hash: str,
        source_image: str,
        receipt_id: str,
    ) -> None:
        """Record successful processing.

        Args:
            file_hash: SHA256 hash of the image
            source_image: Original filename
            receipt_id: ID of the created receipt
        """
        self._cache[file_hash] = CacheEntry(
            file_hash=file_hash,
            source_image=source_image,
            processed_at=datetime.now(),
            status="success",
            receipt_id=receipt_id,
        )
        self._save()

    def add_failure(
        self,
        file_hash: str,
        source_image: str,
        error_message: str,
    ) -> None:
        """Record failed processing.

        Args:
            file_hash: SHA256 hash of the image
            source_image: Original filename
            error_message: Error description
        """
        self._cache[file_hash] = CacheEntry(
            file_hash=file_hash,
            source_image=source_image,
            processed_at=datetime.now(),
            status="failed",
            error_message=error_message,
        )
        self._save()

    def remove(self, file_hash: str) -> bool:
        """Remove an entry from cache.

        Args:
            file_hash: SHA256 hash to remove

        Returns:
            True if entry was removed, False if not found
        """
        if file_hash in self._cache:
            del self._cache[file_hash]
            self._save()
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache = {}
        self._save()

    def get_all_processed(self) -> list[CacheEntry]:
        """Get all successfully processed entries.

        Returns:
            List of successful cache entries
        """
        return [
            entry for entry in self._cache.values()
            if entry.status == "success"
        ]

    def get_all_failed(self) -> list[CacheEntry]:
        """Get all failed entries.

        Returns:
            List of failed cache entries
        """
        return [
            entry for entry in self._cache.values()
            if entry.status == "failed"
        ]

    @property
    def stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dict with success_count, failed_count, total_count
        """
        success = sum(1 for e in self._cache.values() if e.status == "success")
        failed = sum(1 for e in self._cache.values() if e.status == "failed")
        return {
            "success_count": success,
            "failed_count": failed,
            "total_count": len(self._cache),
        }
