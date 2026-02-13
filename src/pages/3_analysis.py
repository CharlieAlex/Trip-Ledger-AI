"""Analysis page - Charts and statistics visualization."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config import Config
from src.etl.storage import ReceiptStorage
from src.ui.sidebar import render_sidebar

st.set_page_config(
    page_title="分析 | Trip Ledger AI",
    page_icon="📊",
    layout="wide",
)

# Sidebar
render_sidebar()

st.title("📊 消費分析")

# Load data
storage = ReceiptStorage()
receipts_df = storage.load_receipts()
items_df = storage.load_items()

if len(receipts_df) == 0:
    st.info("尚無發票資料，請先上傳發票照片。")
    if st.button("前往上傳頁面"):
        st.switch_page("pages/1_upload.py")
    st.stop()

# Overview metrics
st.markdown("### 📈 消費概覽")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📝 發票總數", len(receipts_df))
with col2:
    st.metric("📦 品項總數", len(items_df))
with col3:
    st.metric("💰 消費總額", f"{receipts_df['total'].sum():,.0f}")
with col4:
    if len(receipts_df) > 0:
        unique_stores = receipts_df["store_name"].nunique()
        st.metric("🏪 店家數", unique_stores)

st.markdown("---")

# Tabs for different analyses
tab1, tab2, tab3, tab4 = st.tabs(["🏷️ 類別分析", "📅 每日趨勢", "🏪 店家分析", "📦 品項明細"])

with tab1:
    st.markdown("### 類別消費分布")

    if len(items_df) > 0:
        # Prepare data with labels
        items_df["category_label"] = items_df["category"].apply(
            lambda x: f"{Config.get_category_emoji(x)} {Config.get_category_label(x)}"
        )

        # Subcategory chart colored by main category
        items_df["subcategory_display"] = items_df.apply(
            lambda x: (
                x["subcategory"]
                if x["subcategory"]
                else "(未分類)"
            ),
            axis=1,
        )

        sub_data = items_df.groupby(["category_label", "subcategory_display"]).agg(
            total=("total_price", "sum")
        ).reset_index()
        sub_data = sub_data.sort_values("total", ascending=True)

        fig = px.bar(
            sub_data,
            x="total",
            y="subcategory_display",
            orientation="h",
            title="各類別消費金額（子類別）",
            labels={"total": "金額", "subcategory_display": "子類別", "category_label": "大類別"},
            text_auto=".2s",
            height=max(400, len(sub_data) * 30),
            color="category_label",
        )
        fig.update_layout(
            legend_title_text="大類別",
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig, width="stretch")

    else:
        st.info("尚無品項資料")

with tab2:
    st.markdown("### 每日消費趨勢")

    if len(receipts_df) > 0:
        # Daily totals
        daily_data = receipts_df.groupby("date").agg({
            "total": "sum",
            "receipt_id": "count",
        }).reset_index()
        daily_data.columns = ["date", "total", "count"]
        daily_data["date"] = pd.to_datetime(daily_data["date"])
        daily_data = daily_data.sort_values("date")

        # Bar chart with capped width
        n_days = len(daily_data)
        bar_width_ms = min(0.8, 8 / max(n_days, 1)) * 86400000  # ms per day, cap width

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=daily_data["date"],
            y=daily_data["total"],
            name="消費金額",
            marker_color="steelblue",
            width=bar_width_ms,
        ))
        fig.update_layout(
            title="每日消費金額",
            xaxis_title="日期",
            yaxis_title="金額",
            xaxis={"type": "date", "tickformat": "%Y-%m-%d"},
            bargap=0.3,
        )
        st.plotly_chart(fig, width="stretch")

        # Receipt count chart
        fig2 = px.line(
            daily_data,
            x="date",
            y="count",
            title="每日發票數量",
            markers=True,
        )
        fig2.update_layout(
            xaxis={"type": "date", "tickformat": "%Y-%m-%d"},
        )
        st.plotly_chart(fig2, width="stretch")

with tab3:
    st.markdown("### 🏪 店家分析")

    if len(receipts_df) > 0:
        # Store Chart - Prepare Data
        show_translated = st.session_state.get("show_translated", True)

        receipts_df["display_name"] = receipts_df.apply(
            lambda x: x["store_name_translated"]
            if show_translated and pd.notna(x["store_name_translated"]) and x["store_name_translated"]
            else x["store_name"],
            axis=1
        )

        # Aggregate: total amount per store
        store_amount = receipts_df.groupby("display_name").agg({
            "total": "sum",
        }).reset_index()
        store_amount.columns = ["store", "total_amount"]

        # Aggregate: item count per store (join items with receipts)
        if len(items_df) > 0:
            items_with_store = items_df.merge(
                receipts_df[["receipt_id", "display_name"]].drop_duplicates(),
                on="receipt_id",
                how="left",
            )
            store_item_count = items_with_store.groupby("display_name").size().reset_index(name="item_count")
            store_item_count.columns = ["store", "item_count"]
        else:
            store_item_count = pd.DataFrame(columns=["store", "item_count"])

        col1, col2 = st.columns(2)

        with col1:
            # Chart 1: By Amount
            top_amount = store_amount.sort_values("total_amount", ascending=True).tail(15)
            fig1 = px.bar(
                top_amount,
                x="total_amount",
                y="store",
                orientation="h",
                title="店家消費總額排名 (前15名)",
                labels={"total_amount": "金額", "store": "店家"},
                text_auto=".2s",
                color="total_amount",
                color_continuous_scale="Oranges"
            )
            fig1.update_layout(showlegend=False)
            st.plotly_chart(fig1, width="stretch")

        with col2:
            # Chart 2: By Item Count
            if len(store_item_count) > 0:
                top_items = store_item_count.sort_values("item_count", ascending=True).tail(15)
                fig2 = px.bar(
                    top_items,
                    x="item_count",
                    y="store",
                    orientation="h",
                    title="店家商品數量排名 (前15名)",
                    labels={"item_count": "商品數量", "store": "店家"},
                    text_auto=True,
                    color="item_count",
                    color_continuous_scale="Purples"
                )
                fig2.update_layout(showlegend=False)
                st.plotly_chart(fig2, width="stretch")
            else:
                st.info("尚無品項資料")

    else:
        st.info("尚無發票資料")

with tab4:
    st.markdown("### 品項明細")

    if len(items_df) > 0:
        # Add category display columns
        display_df = items_df.copy()
        display_df["category_display"] = display_df["category"].apply(
            lambda x: f"{Config.get_category_emoji(x)} {Config.get_category_label(x)}"
        )
        display_df["subcategory_display"] = display_df["subcategory"].fillna("(未分類)")

        # Add display name - Do this BEFORE filtering
        show_translated = st.session_state.get("show_translated", True)
        if show_translated:
            display_df["name_display"] = display_df.apply(
                lambda x: (x["name_translated"]
                    if pd.notna(x.get("name_translated")) and x["name_translated"]
                    else x["name"]
                ),
                axis=1
            )
        else:
            display_df["name_display"] = display_df["name"]

        # Filters
        col1, col2 = st.columns(2)
        with col1:
            categories = ["全部"] + sorted(display_df["category_display"].unique().tolist())
            selected_category = st.selectbox("篩選大類別", categories)

        # Filter by main category first
        filtered = display_df.copy()
        if selected_category != "全部":
            filtered = filtered[filtered["category_display"] == selected_category]

        with col2:
            subcategories = ["全部"] + sorted(filtered["subcategory_display"].unique().tolist())
            selected_subcategory = st.selectbox("篩選子類別", subcategories)

        if selected_subcategory != "全部":
            filtered = filtered[filtered["subcategory_display"] == selected_subcategory]

        table_df = filtered[[
            "name_display", "category_display", "subcategory_display", "quantity", "total_price"
        ]].copy()
        table_df.columns = ["品項名稱", "大類別", "子類別", "數量", "金額"]
        st.dataframe(table_df, width="stretch", hide_index=True)

        # Download
        st.download_button(
            "📥 下載品項資料 (CSV)",
            items_df.to_csv(index=False).encode("utf-8"),
            "items.csv",
            "text/csv",
        )
    else:
        st.info("尚無品項資料")
