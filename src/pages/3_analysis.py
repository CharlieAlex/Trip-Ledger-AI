"""Analysis page - Charts and statistics visualization."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config import Config
from src.etl.storage import ReceiptStorage

st.set_page_config(
    page_title="分析 | Trip Ledger AI",
    page_icon="📊",
    layout="wide",
)

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
        # Category totals
        category_data = items_df.groupby("category")["total_price"].sum().reset_index()
        category_data.columns = ["category", "total"]

        # Add emoji and labels
        category_data["emoji"] = category_data["category"].apply(Config.get_category_emoji)
        category_data["label"] = category_data["category"].apply(Config.get_category_label)
        category_data["display"] = category_data["emoji"] + " " + category_data["label"]
        category_data = category_data.sort_values("total", ascending=True)

        col1, col2 = st.columns(2)

        with col1:
            # Bar chart
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
            st.plotly_chart(fig, width='stretch')

        with col2:
            # Pie chart
            fig = px.pie(
                category_data,
                values="total",
                names="display",
                title="消費比例",
                hole=0.4,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, width='stretch')

        # Category table
        st.markdown("### 類別明細")
        table_data = category_data[["display", "total"]].copy()
        table_data.columns = ["類別", "消費金額"]
        table_data["消費金額"] = table_data["消費金額"].apply(lambda x: f"{x:,.0f}")
        st.dataframe(table_data.sort_values("類別"), width='stretch', hide_index=True)
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
        daily_data = daily_data.sort_values("date")

        # Line chart
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
        st.plotly_chart(fig, width='stretch')

        # Receipt count chart
        fig2 = px.line(
            daily_data,
            x="date",
            y="count",
            title="每日發票數量",
            markers=True,
        )
        st.plotly_chart(fig2, width='stretch')

with tab3:
    st.markdown("### 店家消費統計")

    if len(receipts_df) > 0:
        # Store totals
        store_data = receipts_df.groupby("store_name").agg({
            "total": "sum",
            "receipt_id": "count",
        }).reset_index()
        store_data.columns = ["store", "total", "visits"]
        store_data = store_data.sort_values("total", ascending=False)

        # Top stores
        top_n = min(10, len(store_data))
        top_stores = store_data.head(top_n)

        fig = px.bar(
            top_stores,
            x="total",
            y="store",
            orientation="h",
            title=f"消費最高的 {top_n} 家店",
            labels={"total": "消費金額", "store": "店家"},
            color="visits",
            color_continuous_scale="Oranges",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width='stretch')

        # Store table
        st.markdown("### 店家明細")
        table_data = store_data.copy()
        table_data.columns = ["店家", "消費金額", "光顧次數"]
        table_data["消費金額"] = table_data["消費金額"].apply(lambda x: f"{x:,.0f}")
        st.dataframe(table_data, width='stretch', hide_index=True)

with tab4:
    st.markdown("### 品項明細")

    if len(items_df) > 0:
        # Add category display
        display_df = items_df.copy()
        display_df["category_display"] = display_df["category"].apply(
            lambda x: f"{Config.get_category_emoji(x)} {Config.get_category_label(x)}"
        )

        # Filters
        col1, col2 = st.columns(2)
        with col1:
            categories = ["全部"] + list(display_df["category_display"].unique())
            selected_category = st.selectbox("篩選類別", categories)

        if selected_category != "全部":
            display_df = display_df[display_df["category_display"] == selected_category]

        # Display table
        table_df = display_df[["name", "category_display", "quantity", "total_price"]].copy()
        table_df.columns = ["品項名稱", "類別", "數量", "金額"]
        st.dataframe(table_df, width='stretch', hide_index=True)

        # Download
        st.download_button(
            "📥 下載品項資料 (CSV)",
            items_df.to_csv(index=False).encode("utf-8"),
            "items.csv",
            "text/csv",
        )
    else:
        st.info("尚無品項資料")
