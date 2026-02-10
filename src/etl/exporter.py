"""Export functionality for reports.

Supports Excel and PDF export formats.
"""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
from fpdf import FPDF
from loguru import logger

from src.config import Config
from src.etl.storage import ReceiptStorage


class ReportExporter:
    """Export receipts data to various formats."""

    def __init__(self, data_dir: Path | None = None):
        """Initialize exporter.

        Args:
            data_dir: Directory containing CSV data
        """
        self.storage = ReceiptStorage(data_dir)
        self.exports_dir = Config.EXPORTS_DIR
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def export_excel(self, output_path: Path | None = None) -> Path:
        """Export data to Excel format.

        Args:
            output_path: Output file path (default: auto-generated)

        Returns:
            Path to created Excel file
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.exports_dir / f"trip_report_{timestamp}.xlsx"

        receipts_df = self.storage.load_receipts()
        items_df = self.storage.load_items()

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # Summary sheet
            summary = self._create_summary(receipts_df, items_df)
            summary.to_excel(writer, sheet_name="摘要", index=False)

            # Daily spending sheet
            if len(receipts_df) > 0:
                daily = self._create_daily_summary(receipts_df)
                daily.to_excel(writer, sheet_name="每日消費", index=False)

            # Category breakdown sheet
            if len(items_df) > 0:
                category = self._create_category_summary(items_df)
                category.to_excel(writer, sheet_name="類別統計", index=False)

            # Receipts detail sheet
            if len(receipts_df) > 0:
                receipts_df.to_excel(writer, sheet_name="發票明細", index=False)

            # Items detail sheet
            if len(items_df) > 0:
                items_df.to_excel(writer, sheet_name="品項明細", index=False)

        return output_path

    def export_pdf(self, output_path: Path | None = None) -> Path:
        """Export data to PDF format.

        Args:
            output_path: Output file path (default: auto-generated)

        Returns:
            Path to created PDF file
        """

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.exports_dir / f"trip_report_{timestamp}.pdf"

        receipts_df = self.storage.load_receipts()
        items_df = self.storage.load_items()

        pdf = FPDF()
        pdf.add_page()

        # Try to use a font that supports CJK characters
        # Default to helvetica if CJK font not available
        pdf.set_font("Helvetica", size=16)

        # Title
        pdf.cell(0, 10, "Trip Ledger AI Report", ln=True, align="C")
        pdf.ln(5)

        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
        pdf.ln(10)

        # Summary section
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Summary", ln=True)
        pdf.set_font("Helvetica", size=10)

        stats = self.storage.stats
        pdf.cell(0, 8, f"Total Receipts: {stats['receipt_count']}", ln=True)
        pdf.cell(0, 8, f"Total Items: {stats['item_count']}", ln=True)
        pdf.cell(0, 8, f"Total Spending: {stats['total_spending']:.0f}", ln=True)
        if stats['currencies']:
            pdf.cell(0, 8, f"Currencies: {', '.join(stats['currencies'])}", ln=True)
        pdf.ln(10)

        # Daily spending section
        if len(receipts_df) > 0:
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, "Daily Spending", ln=True)
            pdf.set_font("Helvetica", size=10)

            daily = self._create_daily_summary(receipts_df)
            for _, row in daily.iterrows():
                pdf.cell(0, 8, f"{row['date']}: {row['total']:.0f} ({row['receipt_count']} receipts)", ln=True)
            pdf.ln(10)

        # Category breakdown section
        if len(items_df) > 0:
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, "Category Breakdown", ln=True)
            pdf.set_font("Helvetica", size=10)

            category = self._create_category_summary(items_df)
            for _, row in category.iterrows():
                _ = Config.get_category_emoji(row['category'])
                label = Config.get_category_label(row['category'])
                pdf.cell(0, 8, f"{label}: {row['total_price']:.0f} ({row['item_count']} items)", ln=True)

        pdf.output(output_path)
        return output_path

    def _create_summary(self, receipts_df: pd.DataFrame, items_df: pd.DataFrame) -> pd.DataFrame:
        """Create summary DataFrame."""
        stats = self.storage.stats

        data = [
            {"項目": "發票數量", "數值": stats["receipt_count"]},
            {"項目": "品項數量", "數值": stats["item_count"]},
            {"項目": "總消費金額", "數值": f"{stats['total_spending']:.0f}"},
        ]

        if stats["currencies"]:
            data.append({"項目": "使用幣別", "數值": ", ".join(stats["currencies"])})

        if len(receipts_df) > 0:
            dates = pd.to_datetime(receipts_df["date"])
            data.append({"項目": "消費期間", "數值": f"{dates.min().date()} ~ {dates.max().date()}"})

        return pd.DataFrame(data)

    @staticmethod
    def _create_daily_summary(receipts_df: pd.DataFrame) -> pd.DataFrame:
        """Create daily summary DataFrame."""
        daily = receipts_df.groupby("date").agg({
            "total": "sum",
            "receipt_id": "count",
        }).reset_index()
        daily.columns = ["date", "total", "receipt_count"]
        return daily.sort_values("date")

    @staticmethod
    def _create_category_summary(items_df: pd.DataFrame) -> pd.DataFrame:
        """Create category summary DataFrame."""
        category = items_df.groupby("category").agg({
            "total_price": "sum",
            "item_id": "count",
        }).reset_index()
        category.columns = ["category", "total_price", "item_count"]
        return category.sort_values("total_price", ascending=False)

    def generate_share_link(self) -> str:
        """Generate a shareable summary text.

        Returns:
            Formatted text summary
        """
        stats = self.storage.stats
        receipts_df = self.storage.load_receipts()
        items_df = self.storage.load_items()

        lines = [
            "🧾 Trip Ledger AI 消費報告",
            "=" * 30,
            f"📊 總發票數: {stats['receipt_count']}",
            f"💰 總消費: {stats['total_spending']:.0f}",
        ]

        if len(receipts_df) > 0:
            dates = pd.to_datetime(receipts_df["date"])
            lines.append(f"📅 期間: {dates.min().date()} ~ {dates.max().date()}")

        if len(items_df) > 0:
            lines.append("")
            lines.append("📦 類別統計:")
            category = self._create_category_summary(items_df)
            for _, row in category.head(5).iterrows():
                emoji = Config.get_category_emoji(row["category"])
                label = Config.get_category_label(row["category"])
                lines.append(f"  {emoji} {label}: {row['total_price']:.0f}")

        lines.append("")
        lines.append("Generated by Trip Ledger AI")

        return "\n".join(lines)


def main():
    """CLI entry point for export."""
    parser = argparse.ArgumentParser(description="Export trip data to various formats")
    parser.add_argument(
        "--format", "-f",
        choices=["excel", "pdf", "text"],
        default="excel",
        help="Export format",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path",
    )

    args = parser.parse_args()

    exporter = ReportExporter()

    if args.format == "excel":
        output = args.output and Path(args.output)
        path = exporter.export_excel(output)
        logger.info(f"✅ Exported to: {path}")

    elif args.format == "pdf":
        output = args.output and Path(args.output)
        path = exporter.export_pdf(output)
        logger.info(f"✅ Exported to: {path}")

    elif args.format == "text":
        text = exporter.generate_share_link()
        logger.info(text)


if __name__ == "__main__":
    main()
