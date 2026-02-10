#!/usr/bin/env python3
"""Category Classifier Skill - CLI Script.

Usage:
    uv run python .agent/skills/category-classifier/scripts/classify.py "商品名稱"
    uv run python .agent/skills/category-classifier/scripts/classify.py --file items.txt
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
from src.extractors.category_classifier import CategoryClassifier  # noqa: E402


def main():
    """Main entry point for Category Classifier Skill."""
    parser = argparse.ArgumentParser(
        description="Category Classifier Skill - Classify items into categories"
    )
    parser.add_argument(
        "item",
        nargs="?",
        type=str,
        help="Item name to classify",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="File with item names (one per line)",
    )
    parser.add_argument(
        "--context", "-c",
        type=str,
        help="Optional context (e.g., store type)",
    )

    args = parser.parse_args()

    classifier = CategoryClassifier()

    if args.file:
        # Process file
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            sys.exit(1)

        with open(file_path, "r", encoding="utf-8") as f:
            items = [line.strip() for line in f if line.strip()]

        print(f"📦 Classifying {len(items)} items")
        print("-" * 50)

        for item in items:
            category = classifier.classify(item, args.context)
            subcategory = classifier.get_subcategory(item, category)
            info = classifier.get_category_info(category)

            subcat_str = f" ({subcategory})" if subcategory else ""
            print(f"{info['emoji']} {item}: {category.value}{subcat_str}")

    elif args.item:
        # Classify single item
        category = classifier.classify(args.item, args.context)
        subcategory = classifier.get_subcategory(args.item, category)
        info = classifier.get_category_info(category)

        print(f"Item: {args.item}")
        print(f"Category: {info['emoji']} {category.value} ({info['label']})")
        if subcategory:
            print(f"Subcategory: {subcategory}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
