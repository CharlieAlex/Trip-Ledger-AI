"""Invoice parser - main orchestrator for invoice extraction.

Coordinates image preprocessing, API calls, and data storage.
"""

import argparse
import sys
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from loguru import logger

from src.config import Config
from src.etl.cache import ProcessingCache
from src.etl.models import (
    Category,
    Currency,
    Item,
    ProcessingResult,
    Receipt,
)
from src.extractors.category_classifier import CategoryClassifier
from src.extractors.client import GeminiClient, HuggingFaceClient
from src.extractors.image_preprocessor import ImagePreprocessor, get_image_hash


class InvoiceParser:
    """Main invoice parsing orchestrator."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        """Initialize parser.

        Args:
            api_key: Optional API key for the provider
            provider: Optional provider override ('gemini' or 'huggingface')
        """
        self.provider = provider or Config.EXTRACTION_PROVIDER

        if self.provider == "huggingface":
            self.extractor = HuggingFaceClient(api_key=api_key)
        else:
            self.extractor = GeminiClient(api_key=api_key)

        self.preprocessor = ImagePreprocessor()
        self.classifier = CategoryClassifier()
        self.cache = ProcessingCache()

    def process_image(self, image_path: str | Path) -> ProcessingResult:
        """Process a single invoice image.

        Args:
            image_path: Path to the image file

        Returns:
            ProcessingResult with success status and data
        """
        image_path = Path(image_path)
        start_time = time.time()

        # Validate file
        if not image_path.exists():
            return ProcessingResult(
                source_image=str(image_path),
                success=False,
                error_message=f"File not found: {image_path}",
            )

        if not ImagePreprocessor.is_supported_format(image_path):
            return ProcessingResult(
                source_image=str(image_path),
                success=False,
                error_message=f"Unsupported format: {image_path.suffix}",
            )

        # Check cache
        file_hash = get_image_hash(image_path)
        if self.cache.is_processed(file_hash):
            return ProcessingResult(
                source_image=str(image_path),
                success=True,
                error_message="Already processed (cached)",
                processing_time_ms=0,
            )

        try:
            # Preprocess image
            processed_path = self.preprocessor.process(image_path)

            # Extract data via selected provider
            raw_data = self.extractor.extract_invoice_data(processed_path)

            # Convert to Receipt model
            receipt = self._create_receipt(raw_data, image_path, file_hash)

            # Cache success
            self.cache.add_success(file_hash, image_path.name, receipt.receipt_id)

            processing_time = int((time.time() - start_time) * 1000)

            return ProcessingResult(
                source_image=str(image_path),
                success=True,
                receipt=receipt,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            error_msg = str(e)
            self.cache.add_failure(file_hash, image_path.name, error_msg)

            processing_time = int((time.time() - start_time) * 1000)

            return ProcessingResult(
                source_image=str(image_path),
                success=False,
                error_message=error_msg,
                processing_time_ms=processing_time,
            )

    def _create_receipt(
        self,
        raw_data: dict,
        source_path: Path,
        file_hash: str,
    ) -> Receipt:
        """Create Receipt model from raw API data.

        Args:
            raw_data: Dictionary from Gemini API
            source_path: Original image path
            file_hash: SHA256 hash of image

        Returns:
            Receipt model instance
        """
        # Generate receipt ID
        # Generate receipt ID
        receipt_id = file_hash[:16]

        total_decimal = self._to_decimal(raw_data.get("total", 0))

        # Parse timestamp
        timestamp = self._parse_timestamp(raw_data.get("timestamp"))

        # Parse currency
        currency_str = raw_data.get("currency", "JPY")
        try:
            currency = Currency(currency_str)
        except ValueError:
            currency = Currency.JPY

        # Parse items
        items = self._parse_items(raw_data.get("items", []), receipt_id)

        # Create receipt
        receipt = Receipt(
            receipt_id=receipt_id,
            timestamp=timestamp,
            store_name=raw_data.get("store_name", "Unknown"),
            store_name_translated=raw_data.get("store_name_translated"),
            store_address=raw_data.get("store_address"),
            items=items,
            subtotal=self._to_decimal(raw_data.get("subtotal")),
            tax=self._to_decimal(raw_data.get("tax")),
            total=total_decimal,
            currency=currency,
            original_language=raw_data.get("original_language", "unknown"),
            source_image=source_path.name,
            notes=raw_data.get("notes"),
        )

        # Tax/Subtotal logic: if subtotal missing, default to total (assuming tax included/exempt)
        if receipt.subtotal is None:
            receipt.subtotal = receipt.total

        # If tax is None, set to 0? Or leave as None? User didn't specify, but usually safe to say 0 or None.
        if receipt.tax is None and receipt.subtotal == receipt.total:
            # Implies 0 tax or tax included but unknown.
            pass

        return receipt

    def _parse_items(self, items_data: list, receipt_id: str) -> list[Item]:
        """Parse item list from raw data.

        Args:
            items_data: List of item dictionaries
            receipt_id: Parent receipt ID

        Returns:
            List of Item models
        """
        items = []
        for i, item_data in enumerate(items_data):
            # Parse category
            category_str = item_data.get("category", "other")
            try:
                category = Category(category_str)
            except ValueError:
                # Use classifier as fallback
                category, _ = self.classifier.classify(
                    item_data.get("name", ""),
                    None
                ), None
                if isinstance(category, tuple):
                    category = category[0]

            item = Item(
                item_id=f"{receipt_id}_item_{i:03d}",
                receipt_id=receipt_id,
                name=item_data.get("name", "Unknown item"),
                name_translated=item_data.get("name_translated"),
                quantity=item_data.get("quantity", 1),
                unit_price=self._to_decimal(item_data.get("unit_price", 0)),
                total_price=self._to_decimal(item_data.get("total_price", 0)),
                category=category,
                subcategory=item_data.get("subcategory"),
            )
            items.append(item)

        return items

    @staticmethod
    def _parse_timestamp(timestamp_str: Optional[str]) -> datetime:
        """Parse timestamp string to datetime.

        Args:
            timestamp_str: ISO format or various date formats

        Returns:
            datetime object (defaults to now if parsing fails)
        """
        if not timestamp_str:
            return datetime.now()

        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        return datetime.now()

    @staticmethod
    def _to_decimal(value) -> Optional[Decimal]:
        """Convert value to Decimal.

        Args:
            value: Number or string

        Returns:
            Decimal or None
        """
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None

    def process_directory(
        self,
        directory: Path | None = None,
        progress_callback=None,
    ) -> list[ProcessingResult]:
        """Process all images in a directory.

        Args:
            directory: Directory path (defaults to Config.PHOTOS_DIR)
            progress_callback: Optional callback(current, total, filename)

        Returns:
            List of ProcessingResult for each image
        """
        directory = directory or Config.PHOTOS_DIR
        directory = Path(directory)

        if not directory.exists():
            return []

        # Find all supported images
        images = []
        for ext in Config.SUPPORTED_IMAGE_EXTENSIONS:
            images.extend(directory.glob(f"*{ext}"))
            images.extend(directory.glob(f"*{ext.upper()}"))

        results = []
        total = len(images)

        for i, image_path in enumerate(sorted(images)):
            if progress_callback:
                progress_callback(i + 1, total, image_path.name)

            result = self.process_image(image_path)
            results.append(result)

        return results


def main():
    """CLI entry point for invoice parsing."""
    parser = argparse.ArgumentParser(
        description="Extract invoice data from photos"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Process a single image file",
    )
    parser.add_argument(
        "--dir", "-d",
        type=str,
        default=str(Config.PHOTOS_DIR),
        help="Directory containing invoice photos",
    )

    args = parser.parse_args()

    # Check API key configuration
    if Config.EXTRACTION_PROVIDER == "huggingface":
        if not Config.is_hf_configured():
            logger.error("HUGGINGFACE_TOKEN not configured")
            logger.error("Set it in .env file or as environment variable")
            sys.exit(1)
    elif not Config.is_gemini_configured():
        logger.error("GEMINI_API_KEY not configured")
        logger.error("Set it in .env file or as environment variable")
        sys.exit(1)

    invoice_parser = InvoiceParser()

    if args.file:
        # Process single file
        logger.info(f"Processing: {args.file}")
        result = invoice_parser.process_image(args.file)

        if result.success:
            if result.receipt:
                logger.success(f"✓ Success: {result.receipt.store_name}")
                logger.info(f"  Total: {result.receipt.total} {result.receipt.currency.value}")
                logger.info(f"  Items: {len(result.receipt.items)}")
            else:
                logger.info("✓ Already processed (cached)")
        else:
            logger.error(f"✗ Failed: {result.error_message}")
    else:
        # Process directory
        logger.info(f"Processing directory: {args.dir}")

        def progress(current, total, filename):
            logger.info(f"[{current}/{total}] {filename}")

        results = invoice_parser.process_directory(
            Path(args.dir),
            progress_callback=progress,
        )

        # Summary
        success = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        logger.info(f"\nComplete: {success} success, {failed} failed")


if __name__ == "__main__":
    main()
