"""Shared sidebar UI component."""

import streamlit as st

from src.config import Config
from src.etl.storage import ReceiptStorage


def render_sidebar():
    """Render the shared sidebar with language toggle and stats."""
    with st.sidebar:
        st.title("🧾 Trip Ledger AI")

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

        # API status
        if Config.is_gemini_configured():
            st.success("✅ Gemini API 已設定")
        else:
            st.warning("⚠️ 請設定 Gemini API Key")

        if Config.is_maps_configured():
            st.success("✅ Google Maps API 已設定")
        else:
            st.info("ℹ️ Google Maps API 未設定")

        st.markdown("---")

        # Quick stats
        storage = ReceiptStorage()
        stats = storage.stats

        st.metric("📝 發票數量", stats["receipt_count"])
        st.metric("📦 品項數量", stats["item_count"])
        if stats["total_spending"] > 0:
            st.metric("💰 總消費", f"{stats['total_spending']:,.0f}")
