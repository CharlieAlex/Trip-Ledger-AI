"""Timeline page - Daily expense timeline visualization."""


import altair as alt
import pandas as pd
import streamlit as st

from src.config import Config
from src.etl.storage import ReceiptStorage
from src.ui.sidebar import render_sidebar

st.set_page_config(
    page_title="時間線 | Trip Ledger AI",
    page_icon="📅",
    layout="wide",
)

render_sidebar()

st.title("📅 消費時間線")

# Load data
storage = ReceiptStorage()
receipts_df = storage.load_receipts()
items_df = storage.load_items()

if len(receipts_df) == 0:
    st.info("尚無發票資料，請先上傳發票照片。")
    if st.button("前往上傳頁面"):
        st.switch_page("pages/1_upload.py")
    st.stop()

# Date filter
st.markdown("### 篩選日期")
col1, col2 = st.columns(2)

# Parse dates
receipts_df["date_parsed"] = pd.to_datetime(receipts_df["date"])
min_date = receipts_df["date_parsed"].min().date()
max_date = receipts_df["date_parsed"].max().date()

with col1:
    start_date = st.date_input("開始日期", value=min_date, min_value=min_date, max_value=max_date)
with col2:
    end_date = st.date_input("結束日期", value=max_date, min_value=min_date, max_value=max_date)

# Filter data
mask = (receipts_df["date_parsed"].dt.date >= start_date) & (receipts_df["date_parsed"].dt.date <= end_date)
filtered_df = receipts_df[mask].copy()

st.markdown("---")

# Summary
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📝 發票數量", len(filtered_df))
with col2:
    st.metric("💰 消費總額", f"{filtered_df['total'].sum():,.0f}")
with col3:
    if len(filtered_df) > 0:
        avg = filtered_df['total'].mean()
        st.metric("📊 平均消費", f"{avg:,.0f}")

st.markdown("---")

# Visualizations
st.markdown("### 📈 累計消費趨勢")

if len(filtered_df) > 0:
    # Sort by timestamp
    filtered_df["timestamp"] = pd.to_datetime(filtered_df["timestamp"])
    timeline_df = filtered_df.sort_values("timestamp").copy()
    timeline_df["cumulative"] = timeline_df["total"].cumsum()

    # Store display names
    show_translated = st.session_state.get("show_translated", True)
    timeline_df["display_name"] = timeline_df.apply(
        lambda x: x["store_name_translated"]
        if show_translated and pd.notna(x["store_name_translated"]) and x["store_name_translated"]
        else x["store_name"],
        axis=1
    )

    # Insert a starting point at the earliest date 00:00:00 with cumulative = 0
    earliest_date = timeline_df["timestamp"].min().normalize()  # 00:00:00
    origin_row = pd.DataFrame([{
        "timestamp": earliest_date,
        "cumulative": 0,
        "display_name": "",
        "total": 0,
    }])
    timeline_df = pd.concat([origin_row, timeline_df], ignore_index=True)

    # Use date string for x-axis so each day shows only once
    timeline_df["date_label"] = timeline_df["timestamp"].dt.strftime("%Y-%m-%d")

    # Area chart (filled) + line + points
    base = alt.Chart(timeline_df).encode(
        x=alt.X("timestamp:T", title="日期",
                axis=alt.Axis(format="%m/%d", tickCount="day")),
        y=alt.Y("cumulative:Q", title="累計金額"),
    )

    area = base.mark_area(
        opacity=0.2,
        color="#FF4B4B",
    )

    line = base.mark_line(color="#FF4B4B")

    points = base.mark_circle(size=50, color="#FF4B4B").encode(
        tooltip=[
            alt.Tooltip("timestamp:T", title="時間", format="%Y-%m-%d %H:%M"),
            alt.Tooltip("cumulative:Q", title="累計金額", format=",.0f"),
            alt.Tooltip("display_name:N", title="店家"),
            alt.Tooltip("total:Q", title="單筆金額", format=",.0f"),
        ]
    )

    chart = (area + line + points).interactive()
    st.altair_chart(chart, width="stretch")

st.markdown("---")

# Timeline view
st.markdown("### 每日消費")

# Group by date
daily_data = filtered_df.groupby("date").agg({
    "total": "sum",
    "receipt_id": "count",
}).reset_index()
daily_data.columns = ["日期", "消費金額", "發票數"]
daily_data = daily_data.sort_values("日期", ascending=False)

# Create daily cards
for _, row in daily_data.iterrows():
    date_str = row["日期"]
    total = row["消費金額"]
    count = row["發票數"]

    with st.expander(f"📅 {date_str} — 💰 {total:,.0f} ({count} 筆)", expanded=True):
        # Get receipts for this day
        day_receipts = filtered_df[filtered_df["date"] == date_str].sort_values("time")

        for _, receipt in day_receipts.iterrows():
            col1, col2, col3, col4 = st.columns([1, 3, 2, 2])

            with col1:
                st.write(f"🕐 {receipt['time']}")

            with col2:
                store = receipt["store_name"]
                if receipt.get("store_name_translated"):
                    store += f" ({receipt['store_name_translated']})"
                st.write(f"**{store}**")

            with col3:
                st.write(f"💰 {receipt['total']:,.0f} {receipt['currency']}")

            with col4:
                # Get item count
                receipt_items = items_df[items_df["receipt_id"] == receipt["receipt_id"]]
                st.write(f"📦 {len(receipt_items)} 品項")

            # Show items if clicked
            if len(receipt_items) > 0:
                items_data = []
                for _, item in receipt_items.iterrows():
                    emoji = Config.get_category_emoji(item["category"])
                    items_data.append({
                        "": emoji,
                        "品項": item["name"],
                        "數量": item["quantity"],
                        "金額": item["total_price"],
                    })
                st.dataframe(pd.DataFrame(items_data), width='stretch', hide_index=True)

            st.markdown("---")
