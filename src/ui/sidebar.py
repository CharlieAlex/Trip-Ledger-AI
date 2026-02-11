"""Shared sidebar UI component."""

import streamlit as st

from src.config import Config
from src.etl.storage import ReceiptStorage


def render_sidebar():
    """Render the shared sidebar with language toggle and stats."""
    with st.sidebar:
        st.title("🧾 Trip Ledger AI")

        # Navigation
        st.page_link("app.py", label="首頁", icon="🏠")
        st.page_link("pages/1_receipts.py", label="發票管理", icon="🧾")
        st.page_link("pages/2_timeline.py", label="時間軸", icon="📅")
        st.page_link("pages/3_analysis.py", label="統計分析", icon="📊")
        st.page_link("pages/4_map.py", label="地圖", icon="🗺️")
        st.page_link("pages/5_settings.py", label="設定", icon="⚙️")

        st.markdown("---")

        # Language Toggle
        st.markdown("### 🌐 顯示設定")

        # Check if session state has the setting, if not default to True (Translated)
        if "show_translated" not in st.session_state:
            st.session_state.show_translated = True

        st.toggle(
            "顯示翻譯名稱",
            key="show_translated",
            help=f"切換顯示原文 ({Config.DESTINATION_LANGUAGE}) 或翻譯 ({Config.PRIMARY_LANGUAGE})"
        )

        st.markdown(f"**目標語言**: {Config.PRIMARY_LANGUAGE}")
        st.markdown("---")

        # Quick stats
        @st.cache_data(ttl="1m", show_spinner=False)
        def get_cached_stats():
            storage = ReceiptStorage()
            return storage.stats

        stats = get_cached_stats()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("🧾 發票", stats["receipt_count"])
        with col2:
            st.metric("📦 品項", stats["item_count"])

        if stats["total_spending"] > 0:
            st.container().metric("💰 總消費", f"{stats['total_spending']:,.0f}")

        st.markdown("---")

        # API status
        if Config.is_gemini_configured():
            st.success("✅ Gemini API 已設定")
        else:
            st.warning("⚠️ 請設定 Gemini API Key")

        if Config.is_maps_configured():
            st.success("✅ Google Maps API 已設定")
        else:
            st.info("ℹ️ Google Maps API 未設定")
