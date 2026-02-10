"""Map page - Geographic visualization of expenses."""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

from src.config import Config
from src.etl.storage import ReceiptStorage
from src.geo.geocoder import Geocoder

st.set_page_config(
    page_title="地圖 | Trip Ledger AI",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ 消費地圖")

# Load data
storage = ReceiptStorage()
receipts_df = storage.load_receipts()

if len(receipts_df) == 0:
    st.info("尚無發票資料，請先上傳發票照片。")
    if st.button("前往上傳頁面"):
        st.switch_page("pages/1_upload.py")
    st.stop()

# Check for geocoded data
has_location = receipts_df["latitude"].notna() & receipts_df["longitude"].notna()
geocoded_df = receipts_df[has_location]

st.markdown("### 消費地點分布")

# Action buttons
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🔄 更新地理資訊"):
        if not Config.is_maps_configured():
            st.error("請先設定 Google Maps API Key")
        else:
            with st.spinner("取得地理座標中..."):
                geocoder = Geocoder()
                updated = geocoder.geocode_receipts()
                st.success(f"已更新 {updated} 筆座標")
                st.rerun()

with col2:
    # Stats
    st.info(f"共 {len(receipts_df)} 筆發票，{len(geocoded_df)} 筆有座標資料")

if len(geocoded_df) == 0:
    st.warning("尚無地理座標資料")
    st.markdown("""
    可能原因：
    1. 尚未設定 Google Maps API Key
    2. 發票上的店家資訊無法解析

    請點擊「更新地理資訊」按鈕嘗試取得座標。
    """)
    st.stop()

# Create map
# Calculate center
center_lat = geocoded_df["latitude"].mean()
center_lon = geocoded_df["longitude"].mean()

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=12,
    tiles="OpenStreetMap",
)

# Add markers
for _, row in geocoded_df.iterrows():
    # Create popup content
    popup_html = f"""
    <div style="min-width: 200px;">
        <h4>{row['store_name']}</h4>
        <p><b>金額:</b> {row['total']:,.0f} {row['currency']}</p>
        <p><b>日期:</b> {row['date']} {row['time']}</p>
    </div>
    """

    # Marker color based on amount
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

# Display map
st_data = st_folium(m, width=None, height=500)

st.markdown("---")

# Legend
st.markdown("### 圖例")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("🔵 < 1,000")
with col2:
    st.markdown("🟠 1,000 ~ 5,000")
with col3:
    st.markdown("🔴 > 5,000")

st.markdown("---")

# Location summary
st.markdown("### 地點消費統計")

if len(geocoded_df) > 0:
    # Group by approximate location (rounded coordinates)
    geocoded_df = geocoded_df.copy()
    geocoded_df["location_key"] = (
        geocoded_df["latitude"].round(3).astype(str) + "," +
        geocoded_df["longitude"].round(3).astype(str)
    )

    location_stats = geocoded_df.groupby("store_name").agg({
        "total": "sum",
        "receipt_id": "count",
    }).reset_index()
    location_stats.columns = ["店家", "消費總額", "發票數"]
    location_stats = location_stats.sort_values("消費總額", ascending=False)
    location_stats["消費總額"] = location_stats["消費總額"].apply(lambda x: f"{x:,.0f}")

    st.dataframe(location_stats, width='stretch', hide_index=True)
