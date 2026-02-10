"""Chart visualization utilities using Plotly."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config import Config


def create_category_bar_chart(items_df: pd.DataFrame) -> go.Figure:
    """Create horizontal bar chart for category spending.

    Args:
        items_df: Items DataFrame

    Returns:
        Plotly figure
    """
    if len(items_df) == 0:
        return go.Figure()

    category_data = items_df.groupby("category")["total_price"].sum().reset_index()
    category_data.columns = ["category", "total"]

    # Add display labels
    category_data["emoji"] = category_data["category"].apply(Config.get_category_emoji)
    category_data["label"] = category_data["category"].apply(Config.get_category_label)
    category_data["display"] = category_data["emoji"] + " " + category_data["label"]
    category_data = category_data.sort_values("total", ascending=True)

    fig = px.bar(
        category_data,
        x="total",
        y="display",
        orientation="h",
        title="各類別消費金額",
        labels={"total": "金額", "display": "類別"},
        color="total",
        color_continuous_scale="Blues",
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False)

    return fig


def create_category_pie_chart(items_df: pd.DataFrame) -> go.Figure:
    """Create pie chart for category spending distribution.

    Args:
        items_df: Items DataFrame

    Returns:
        Plotly figure
    """
    if len(items_df) == 0:
        return go.Figure()

    category_data = items_df.groupby("category")["total_price"].sum().reset_index()
    category_data.columns = ["category", "total"]

    category_data["label"] = category_data["category"].apply(
        lambda x: f"{Config.get_category_emoji(x)} {Config.get_category_label(x)}"
    )

    fig = px.pie(
        category_data,
        values="total",
        names="label",
        title="消費比例",
        hole=0.4,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")

    return fig


def create_daily_bar_chart(receipts_df: pd.DataFrame) -> go.Figure:
    """Create bar chart for daily spending.

    Args:
        receipts_df: Receipts DataFrame

    Returns:
        Plotly figure
    """
    if len(receipts_df) == 0:
        return go.Figure()

    daily_data = receipts_df.groupby("date")["total"].sum().reset_index()
    daily_data = daily_data.sort_values("date")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=daily_data["date"],
        y=daily_data["total"],
        name="消費金額",
        marker_color="steelblue",
    ))
    fig.update_layout(
        title="每日消費金額",
        xaxis_title="日期",
        yaxis_title="金額",
    )

    return fig


def create_store_bar_chart(receipts_df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Create bar chart for top stores by spending.

    Args:
        receipts_df: Receipts DataFrame
        top_n: Number of top stores to show

    Returns:
        Plotly figure
    """
    if len(receipts_df) == 0:
        return go.Figure()

    store_data = receipts_df.groupby("store_name").agg({
        "total": "sum",
        "receipt_id": "count",
    }).reset_index()
    store_data.columns = ["store", "total", "visits"]
    store_data = store_data.sort_values("total", ascending=False).head(top_n)

    fig = px.bar(
        store_data,
        x="total",
        y="store",
        orientation="h",
        title=f"消費最高的 {top_n} 家店",
        labels={"total": "消費金額", "store": "店家"},
        color="visits",
        color_continuous_scale="Oranges",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})

    return fig
