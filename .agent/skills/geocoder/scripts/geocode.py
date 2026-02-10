#!/usr/bin/env python3
"""Geocoder Skill - CLI Script.

Usage:
    uv run python .agent/skills/geocoder/scripts/geocode.py "地址或店名"
    uv run python .agent/skills/geocoder/scripts/geocode.py --update-receipts
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from src.config import Config
from src.geo.geocoder import Geocoder


def main():
    """Main entry point for Geocoder Skill."""
    parser = argparse.ArgumentParser(
        description="Geocoder Skill - Convert addresses to coordinates"
    )
    parser.add_argument(
        "query",
        nargs="?",
        type=str,
        help="Address or place name to geocode",
    )
    parser.add_argument(
        "--region", "-r",
        type=str,
        default="japan",
        help="Region hint (japan, taiwan, etc.)",
    )
    parser.add_argument(
        "--update-receipts",
        action="store_true",
        help="Batch update receipts with coordinates",
    )

    args = parser.parse_args()

    # Check API configuration
    if not Config.is_maps_configured():
        logger.warning("GOOGLE_MAPS_API_KEY not configured")
        logger.warning("Only cached results will be available.")

    geocoder = Geocoder()

    if args.update_receipts:
        logger.info("📍 Updating receipts with geocoding data...")

        updated = geocoder.geocode_receipts()
        logger.success(f"✅ Updated {updated} receipt(s)")

    elif args.query:
        logger.info(f"🔍 Geocoding: {args.query}")

        result = geocoder.geocode(args.query, region=args.region)

        if result:
            logger.info(f"📍 Latitude: {result.latitude}")
            logger.info(f"📍 Longitude: {result.longitude}")
            if result.formatted_address:
                logger.info(f"📮 Address: {result.formatted_address}")
            if result.place_id:
                logger.info(f"🆔 Place ID: {result.place_id}")
        else:
            logger.error("❌ Could not geocode this query")
            if not Config.is_maps_configured():
                logger.warning("(API key not configured)")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
