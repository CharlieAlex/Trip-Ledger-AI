"""Trip Ledger AI - Main entry point.

This module provides a CLI entry point for the application.
The primary interface is the Streamlit web application (src/app.py).
"""

import argparse
import subprocess
import sys

from src.etl.exporter import main as export_main
from src.extractors.invoice_parser import main as extract_main


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Trip Ledger AI - AI-powered trip expense tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
                # Start the Streamlit web application
                make run

                # Process invoice photos
                make extract

                # Force reprocess all photos
                make extract-force

                # Export to Excel
                make export-excel

            For more commands, run: make help
        """,
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Trip Ledger AI v0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # extract command
    extract_parser = subparsers.add_parser("extract", help="Process invoice photos")
    extract_parser.add_argument("--force", action="store_true", help="Force reprocess")
    extract_parser.add_argument("--file", "-f", type=str, help="Process single file")

    # export command
    export_parser = subparsers.add_parser("export", help="Export report")
    export_parser.add_argument(
        "--format", "-f",
        choices=["excel", "pdf", "text"],
        default="excel",
        help="Export format",
    )

    args = parser.parse_args()

    if args.command == "extract":
        sys.argv = ["invoice_parser"]
        if args.force:
            sys.argv.append("--force")
        if args.file:
            sys.argv.extend(["--file", args.file])
        extract_main()

    elif args.command == "export":
        sys.argv = ["exporter", "--format", args.format]
        export_main()

    elif args.command == "run":
        subprocess.run(["streamlit", "run", "src/app.py"], check=True)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
