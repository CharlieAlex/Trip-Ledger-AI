"""Map visualization utilities using Folium."""

from typing import Optional

import folium
import pandas as pd
from folium.plugins import HeatMap


def create_expense_map(
    receipts_df: pd.DataFrame,
    center: Optional[tuple[float, float]] = None,
    zoom_start: int = 12,
) -> folium.Map:
    """Create a Folium map with expense markers.

    Args:
        receipts_df: Receipts DataFrame with latitude/longitude columns
        center: Optional (lat, lon) tuple for map center
        zoom_start: Initial zoom level

    Returns:
        Folium Map object
    """
    # Filter to only rows with coordinates
    has_location = receipts_df["latitude"].notna() & receipts_df["longitude"].notna()
    geocoded_df = receipts_df[has_location]

    # Calculate center if not provided
    if center is None:
        if len(geocoded_df) > 0:
            center = (
                geocoded_df["latitude"].mean(),
                geocoded_df["longitude"].mean(),
            )
        else:
            # Default to Tokyo
            center = (35.6762, 139.6503)

    # Create map
    m = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles="OpenStreetMap",
    )

    # Add markers
    for _, row in geocoded_df.iterrows():
        popup_html = f"""
        <div style="min-width: 200px;">
            <h4>{row['store_name']}</h4>
            <p><b>金額:</b> {row['total']:,.0f} {row['currency']}</p>
            <p><b>日期:</b> {row['date']} {row.get('time', '')}</p>
        </div>
        """

        # Color based on amount
        if row["total"] > 5000:
            color = "red"
        elif row["total"] > 1000:
            color = "orange"
        else:
            color = "blue"

        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['store_name']}: {row['total']:,.0f}",
            icon=folium.Icon(color=color, icon="info-sign"),
        ).add_to(m)

    return m


def create_heatmap(
    receipts_df: pd.DataFrame,
    center: Optional[tuple[float, float]] = None,
) -> folium.Map:
    """Create a heatmap of expenses.

    Args:
        receipts_df: Receipts DataFrame with latitude/longitude columns
        center: Optional (lat, lon) tuple for map center

    Returns:
        Folium Map object with heatmap layer
    """
    # Create heatmap data
    has_location = receipts_df["latitude"].notna() & receipts_df["longitude"].notna()
    geocoded_df = receipts_df[has_location]

    if center is None:
        if len(geocoded_df) > 0:
            center = (
                geocoded_df["latitude"].mean(),
                geocoded_df["longitude"].mean(),
            )
        else:
            center = (35.6762, 139.6503)

    m = folium.Map(
        location=center,
        zoom_start=12,
        tiles="OpenStreetMap",
    )

    # Create heatmap data
    heat_data = []
    for _, row in geocoded_df.iterrows():
        # Weight by spending amount
        weight = min(row["total"] / 1000, 10)  # Normalize weight
        heat_data.append([row["latitude"], row["longitude"], weight])

    if heat_data:
        HeatMap(heat_data).add_to(m)

    return m
