#!/usr/bin/env python3
"""Invoice Extractor Skill - CLI Script.

Usage:
    uv run python .agent/skills/invoice-extractor/scripts/extract.py
    uv run python .agent/skills/invoice-extractor/scripts/extract.py --file path/to/invoice.jpg
    uv run python .agent/skills/invoice-extractor/scripts/extract.py --force
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import Config
from src.extractors.invoice_parser import InvoiceParser
from src.etl.storage import ReceiptStorage


def main():
    """Main entry point for Invoice Extractor Skill."""
    parser = argparse.ArgumentParser(
        description="Invoice Extractor Skill - Extract structured data from invoice photos"
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
        help="Directory containing invoice photos (default: data/photos/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reprocessing, ignoring cache",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=str(Config.DATA_DIR),
        help="Output directory for CSV files (default: data/)",
    )

    args = parser.parse_args()

    # Check API configuration
    if not Config.is_gemini_configured():
        print("❌ Error: GEMINI_API_KEY not configured")
        print("")
        print("Please set your API key using one of these methods:")
        print("  1. Create a .env file with: GEMINI_API_KEY=your_key_here")
        print("  2. Set environment variable: export GEMINI_API_KEY=your_key_here")
        print("  3. Use the Streamlit UI settings page")
        sys.exit(1)

    print("=" * 60)
    print("🧾 Invoice Extractor Skill")
    print("=" * 60)
    print(f"Model: {Config.GEMINI_MODEL}")
    print(f"Force reprocess: {args.force}")
    print("")

    # Initialize parser and storage
    invoice_parser = InvoiceParser(force_reprocess=args.force)
    storage = ReceiptStorage(Path(args.output))

    if args.file:
        # Process single file
        file_path = Path(args.file)
        print(f"📷 Processing: {file_path.name}")
        print("-" * 40)

        result = invoice_parser.process_image(file_path)

        if result.success and result.receipt:
            receipt = result.receipt
            print(f"✅ Store: {receipt.store_name}")
            if receipt.store_name_translated:
                print(f"   ({receipt.store_name_translated})")
            print(f"💰 Total: {receipt.total} {receipt.currency.value}")
            print(f"📅 Date: {receipt.date} {receipt.time}")
            print(f"📦 Items: {len(receipt.items)}")

            for item in receipt.items:
                emoji = Config.get_category_emoji(item.category.value)
                print(f"   {emoji} {item.name}: {item.total_price}")

            # Save to CSV
            storage.save_receipt(receipt)
            print("")
            print(f"💾 Saved to: {args.output}/")

        elif result.success:
            print("ℹ️  Already processed (cached)")
        else:
            print(f"❌ Failed: {result.error_message}")
            sys.exit(1)

    else:
        # Process directory
        photo_dir = Path(args.dir)
        print(f"📁 Directory: {photo_dir}")
        print("-" * 40)

        if not photo_dir.exists():
            print(f"❌ Directory not found: {photo_dir}")
            sys.exit(1)

        # Count images
        images = []
        for ext in Config.SUPPORTED_IMAGE_EXTENSIONS:
            images.extend(photo_dir.glob(f"*{ext}"))
            images.extend(photo_dir.glob(f"*{ext.upper()}"))

        if not images:
            print("ℹ️  No images found in directory")
            print(f"   Supported formats: {', '.join(Config.SUPPORTED_IMAGE_EXTENSIONS)}")
            sys.exit(0)

        print(f"Found {len(images)} image(s)")
        print("")

        # Process each image
        success_count = 0
        failed_count = 0
        skipped_count = 0
        all_receipts = []

        for i, image_path in enumerate(sorted(images), 1):
            print(f"[{i}/{len(images)}] {image_path.name}...", end=" ")

            result = invoice_parser.process_image(image_path)

            if result.success and result.receipt:
                print(f"✅ {result.receipt.store_name} ({result.receipt.total} {result.receipt.currency.value})")
                all_receipts.append(result.receipt)
                success_count += 1
            elif result.success:
                print("⏭️  Cached")
                skipped_count += 1
            else:
                print(f"❌ {result.error_message}")
                failed_count += 1

        # Save all receipts
        if all_receipts:
            for receipt in all_receipts:
                storage.save_receipt(receipt)

        # Summary
        print("")
        print("=" * 60)
        print("📊 Summary")
        print("=" * 60)
        print(f"✅ Success: {success_count}")
        print(f"⏭️  Skipped (cached): {skipped_count}")
        print(f"❌ Failed: {failed_count}")

        if all_receipts:
            total_amount = sum(r.total for r in all_receipts)
            print(f"💰 Total extracted: {total_amount}")
            print(f"💾 Data saved to: {args.output}/")


if __name__ == "__main__":
    main()
