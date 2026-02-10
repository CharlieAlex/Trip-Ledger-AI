"""Timeline visualization utilities."""

import pandas as pd
from typing import Optional


def create_timeline_view(
    receipts_df: pd.DataFrame,
    items_df: pd.DataFrame,
    date_filter: Optional[tuple[str, str]] = None,
) -> dict:
    """Create timeline data structure for visualization.

    Args:
        receipts_df: Receipts DataFrame
        items_df: Items DataFrame
        date_filter: Optional (start_date, end_date) tuple

    Returns:
        Dict with timeline data organized by date
    """
    if len(receipts_df) == 0:
        return {}

    # Apply date filter if provided
    if date_filter:
        start_date, end_date = date_filter
        mask = (receipts_df["date"] >= start_date) & (receipts_df["date"] <= end_date)
        receipts_df = receipts_df[mask]

    # Group by date
    timeline = {}
    for date in sorted(receipts_df["date"].unique(), reverse=True):
        day_receipts = receipts_df[receipts_df["date"] == date].sort_values("time")

        day_data = {
            "date": date,
            "total": day_receipts["total"].sum(),
            "receipt_count": len(day_receipts),
            "receipts": [],
        }

        for _, receipt in day_receipts.iterrows():
            receipt_items = items_df[items_df["receipt_id"] == receipt["receipt_id"]]

            receipt_data = {
                "receipt_id": receipt["receipt_id"],
                "time": receipt["time"],
                "store_name": receipt["store_name"],
                "store_name_translated": receipt.get("store_name_translated"),
                "total": receipt["total"],
                "currency": receipt["currency"],
                "items": receipt_items.to_dict("records"),
            }
            day_data["receipts"].append(receipt_data)

        timeline[date] = day_data

    return timeline


def format_timeline_text(timeline: dict) -> str:
    """Format timeline as readable text.

    Args:
        timeline: Timeline dict from create_timeline_view

    Returns:
        Formatted text
    """
    lines = []
    for date, day_data in timeline.items():
        lines.append(f"📅 {date} — 💰 {day_data['total']:,.0f}")
        for receipt in day_data["receipts"]:
            lines.append(f"  🕐 {receipt['time']} {receipt['store_name']}: {receipt['total']:,.0f}")
        lines.append("")

    return "\n".join(lines)
