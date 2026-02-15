"""CSV storage for receipts and items."""

from pathlib import Path
from typing import Optional

import pandas as pd

from src.config import Config
from src.etl.models import Receipt


class ReceiptStorage:
    """Handle CSV storage for receipts and items."""

    RECEIPT_COLUMNS = [
        "receipt_id",
        "timestamp",
        "date",
        "time",
        "store_name",
        "store_name_translated",
        "store_address",
        "latitude",
        "longitude",
        "subtotal",
        "tax",
        "total",
        "currency",
        "original_language",
        "source_image",
        "processed_at",
        "notes",
    ]

    ITEM_COLUMNS = [
        "item_id",
        "receipt_id",
        "name",
        "name_translated",
        "quantity",
        "unit_price",
        "total_price",
        "category",
        "subcategory",
    ]

    def __init__(self, data_dir: Path | None = None):
        """Initialize storage.

        Args:
            data_dir: Directory for CSV files (default: Config.DATA_DIR)
        """
        self.data_dir = data_dir or Config.DATA_DIR
        self.receipts_file = self.data_dir / "receipts.csv"
        self.items_file = self.data_dir / "items.csv"

    def save_receipt(self, receipt: Receipt) -> None:
        """Save a receipt and its items to CSV.

        Args:
            receipt: Receipt model to save
        """
        # Prepare receipt data
        receipt_data = {
            "receipt_id": receipt.receipt_id,
            "timestamp": receipt.timestamp.isoformat(),
            "date": receipt.date,
            "time": receipt.time,
            "store_name": receipt.store_name,
            "store_name_translated": receipt.store_name_translated,
            "store_address": receipt.store_address,
            "latitude": receipt.location.latitude if receipt.location else None,
            "longitude": receipt.location.longitude if receipt.location else None,
            "subtotal": float(receipt.subtotal) if receipt.subtotal else None,
            "tax": float(receipt.tax) if receipt.tax else None,
            "total": float(receipt.total),
            "currency": receipt.currency.value,
            "original_language": receipt.original_language,
            "source_image": receipt.source_image,
            "processed_at": receipt.processed_at.isoformat(),
            "notes": receipt.notes,
        }

        # Prepare items data
        items_data = []
        for item in receipt.items:
            items_data.append({
                "item_id": item.item_id,
                "receipt_id": item.receipt_id,
                "name": item.name,
                "name_translated": item.name_translated,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "total_price": float(item.total_price),
                "category": item.category.value,
                "subcategory": item.subcategory,
            })

        # Load existing data or create new
        receipts_df = self._load_or_create_df(self.receipts_file, self.RECEIPT_COLUMNS)
        items_df = self._load_or_create_df(self.items_file, self.ITEM_COLUMNS)

        # Remove existing receipt if updating
        receipts_df = receipts_df[receipts_df["receipt_id"] != receipt.receipt_id]
        items_df = items_df[items_df["receipt_id"] != receipt.receipt_id]

        # Append new data
        new_receipt_df = pd.DataFrame([receipt_data])
        receipts_df = receipts_df.convert_dtypes()
        new_receipt_df = new_receipt_df.astype(receipts_df.dtypes)
        receipts_df = pd.concat([receipts_df, new_receipt_df], ignore_index=True)

        if items_data:
            new_items_df = pd.DataFrame(items_data)
            items_df = pd.concat([items_df, new_items_df], ignore_index=True)

        # Save
        receipts_df.to_csv(self.receipts_file, index=False)
        items_df.to_csv(self.items_file, index=False)

    @staticmethod
    def _load_or_create_df(file_path: Path, columns: list) -> pd.DataFrame:
        """Load existing CSV or create empty DataFrame.

        Args:
            file_path: Path to CSV file
            columns: Column names

        Returns:
            DataFrame
        """
        if file_path.exists():
            try:
                return pd.read_csv(file_path)
            except pd.errors.EmptyDataError:
                pass
        return pd.DataFrame(columns=columns)

    def load_receipts(self) -> pd.DataFrame:
        """Load all receipts.

        Returns:
            DataFrame of receipts
        """
        return self._load_or_create_df(self.receipts_file, self.RECEIPT_COLUMNS)

    def load_items(self) -> pd.DataFrame:
        """Load all items.

        Returns:
            DataFrame of items
        """
        return self._load_or_create_df(self.items_file, self.ITEM_COLUMNS)

    def get_receipt_by_id(self, receipt_id: str) -> Optional[dict]:
        """Get a single receipt by ID.

        Args:
            receipt_id: Receipt ID

        Returns:
            Receipt data dict or None
        """
        df = self.load_receipts()
        matches = df[df["receipt_id"] == receipt_id]
        if len(matches) == 0:
            return None
        return matches.iloc[0].to_dict()

    def get_items_by_receipt(self, receipt_id: str) -> pd.DataFrame:
        """Get items for a receipt.

        Args:
            receipt_id: Receipt ID

        Returns:
            DataFrame of items
        """
        df = self.load_items()
        return df[df["receipt_id"] == receipt_id]

    def get_receipts_by_date_range(
        self,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Get receipts within a date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame of receipts
        """
        df = self.load_receipts()
        if len(df) == 0:
            return df

        df["date"] = pd.to_datetime(df["date"])
        mask = (df["date"] >= start_date) & (df["date"] <= end_date)
        return df[mask]

    def find_duplicates(self) -> dict[str, list[str]]:
        """Find potential duplicate receipts.

        Groups receipts by date, time, and total amount.

        Returns:
            Dict mapping a key (date_time_total) to list of receipt_ids
        """
        df = self.load_receipts()
        if len(df) == 0:
            return {}

        # Create a grouping key
        df["dup_key"] = df.apply(
            lambda x: f"{x['date']}_{x['time']}_{float(x['total']):.2f}",
            axis=1
        )

        # Find duplicates
        dups = df[df.duplicated(subset=["dup_key"], keep=False)]

        if len(dups) == 0:
            return {}

        # Group by key
        result = {}
        for key, group in dups.groupby("dup_key"):
            result[key] = group["receipt_id"].tolist()

        return result

    def get_spending_by_category(self) -> pd.DataFrame:
        """Get total spending by category.

        Returns:
            DataFrame with category and total columns
        """
        items_df = self.load_items()
        if len(items_df) == 0:
            return pd.DataFrame(columns=["category", "total"])

        return items_df.groupby("category")["total_price"].sum().reset_index()

    def get_daily_spending(self) -> pd.DataFrame:
        """Get daily spending totals.

        Returns:
            DataFrame with date and total columns
        """
        receipts_df = self.load_receipts()
        if len(receipts_df) == 0:
            return pd.DataFrame(columns=["date", "total"])

        return receipts_df.groupby("date")["total"].sum().reset_index()

    def delete_receipt(self, receipt_id: str) -> bool:
        """Delete a receipt and its items.

        Args:
            receipt_id: Receipt ID to delete

        Returns:
            True if deleted, False if not found
        """
        receipts_df = self.load_receipts()
        items_df = self.load_items()

        if receipt_id not in receipts_df["receipt_id"].to_numpy():
            return False

        receipts_df = receipts_df[receipts_df["receipt_id"] != receipt_id]
        items_df = items_df[items_df["receipt_id"] != receipt_id]

        receipts_df.to_csv(self.receipts_file, index=False)
        items_df.to_csv(self.items_file, index=False)

        return True

    def update_items(self, receipt_id: str, new_items_df: pd.DataFrame) -> bool:
        """Update items for a receipt.

        Args:
            receipt_id: Receipt ID
            new_items_df: DataFrame containing new items

        Returns:
            True if successful
        """
        # Load existing
        items_df = self.load_items()

        # Remove old items for this receipt
        items_df = items_df[items_df["receipt_id"] != receipt_id]

        # Add new items
        items_df = pd.concat([items_df, new_items_df], ignore_index=True)

        # Save items
        items_df.to_csv(self.items_file, index=False)

        # Recalculate receipt total
        new_total = new_items_df["total_price"].sum()
        self.update_receipt(receipt_id, {"total": new_total})

        return True

    def update_receipt(self, receipt_id: str, updates: dict) -> bool:
        """Update specific fields of a receipt.

        Args:
            receipt_id: Receipt ID
            updates: Dictionary of fields to update

        Returns:
            True if successful
        """
        receipts_df = self.load_receipts()

        if receipt_id not in receipts_df["receipt_id"].to_numpy():
            return False

        # Update fields
        for key, value in updates.items():
            if key in receipts_df.columns:
                receipts_df.loc[receipts_df["receipt_id"] == receipt_id, key] = value

        receipts_df.to_csv(self.receipts_file, index=False)
        return True

    @property
    def stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dict with counts and totals
        """
        receipts_df = self.load_receipts()
        items_df = self.load_items()

        return {
            "receipt_count": len(receipts_df),
            "item_count": len(items_df),
            "total_spending": receipts_df["total"].sum() if len(receipts_df) > 0 else 0,
            "currencies": receipts_df["currency"].unique().tolist() if len(receipts_df) > 0 else [],
        }
