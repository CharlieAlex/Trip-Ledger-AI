"""Pydantic data models for receipts and items."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Category(str, Enum):
    """Item category enumeration."""

    FOOD = "food"
    BEVERAGE = "beverage"
    TRANSPORT = "transport"
    LODGING = "lodging"
    SHOPPING = "shopping"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    OTHER = "other"


class Currency(str, Enum):
    """Supported currencies."""

    TWD = "TWD"
    JPY = "JPY"
    USD = "USD"
    EUR = "EUR"
    KRW = "KRW"
    CNY = "CNY"
    GBP = "GBP"
    HKD = "HKD"


class Item(BaseModel):
    """Individual item from a receipt."""

    item_id: str = Field(..., description="Unique item identifier")
    receipt_id: str = Field(..., description="Parent receipt ID")
    name: str = Field(..., description="Item name (original language)")
    name_translated: Optional[str] = Field(None, description="Translated item name")
    quantity: int = Field(default=1, ge=1, description="Quantity purchased")
    unit_price: Decimal = Field(..., description="Price per unit")
    total_price: Decimal = Field(..., description="Total price for this item")
    category: Category = Field(default=Category.OTHER, description="Item category")
    subcategory: Optional[str] = Field(None, description="Subcategory")


class GeoLocation(BaseModel):
    """Geographic location data."""

    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    formatted_address: Optional[str] = None
    place_id: Optional[str] = None


class Receipt(BaseModel):
    """Receipt/invoice data model."""

    receipt_id: str = Field(..., description="Unique receipt identifier (file hash)")
    timestamp: datetime = Field(..., description="Purchase timestamp")
    store_name: str = Field(..., description="Store name (original language)")
    store_name_translated: Optional[str] = Field(None, description="Translated store name")
    store_address: Optional[str] = Field(None, description="Store address")
    location: Optional[GeoLocation] = Field(None, description="Geographic coordinates")
    items: list[Item] = Field(default_factory=list, description="List of items")
    subtotal: Optional[Decimal] = Field(None, description="Subtotal before tax")
    tax: Optional[Decimal] = Field(None, description="Tax amount")
    total: Decimal = Field(..., description="Total amount")
    currency: Currency = Field(default=Currency.JPY, description="Currency")
    original_language: str = Field(default="unknown", description="Original language of receipt")
    source_image: str = Field(..., description="Source image filename")
    processed_at: datetime = Field(default_factory=datetime.now, description="Processing timestamp")
    notes: Optional[str] = Field(None, description="Additional notes")

    @property
    def item_count(self) -> int:
        """Get total number of items."""
        return sum(item.quantity for item in self.items)

    @property
    def date(self) -> str:
        """Get date string (YYYY-MM-DD)."""
        return self.timestamp.strftime("%Y-%m-%d")

    @property
    def time(self) -> str:
        """Get time string (HH:MM)."""
        return self.timestamp.strftime("%H:%M")


class ProcessingResult(BaseModel):
    """Result of processing a single image."""

    source_image: str
    success: bool
    receipt: Optional[Receipt] = None
    error_message: Optional[str] = None
    processing_time_ms: int = 0


class CacheEntry(BaseModel):
    """Cache entry for processed images."""

    file_hash: str = Field(..., description="SHA256 hash of the image file")
    source_image: str = Field(..., description="Original filename")
    processed_at: datetime = Field(default_factory=datetime.now)
    status: str = Field(..., description="success or failed")
    receipt_id: Optional[str] = None
    error_message: Optional[str] = None
