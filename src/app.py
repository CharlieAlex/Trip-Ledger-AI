"""Trip Ledger AI - Streamlit Application.

Main entry point for the web application.
"""

import streamlit as st
from config import Config
import sys
from pathlib import Path
project_root = Path(__file__).parents[1]
sys.path.append(str(project_root))
from src.etl.storage import ReceiptStorage  # noqa: E402

# Page configuration
st.set_page_config(
    page_title="Trip Ledger AI",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    """Main application entry point."""
    # Initialize session state
    if "initialized" not in st.session_state:
        Config.ensure_directories()
        st.session_state.initialized = True

    # Sidebar
    with st.sidebar:
        st.title("🧾 Trip Ledger AI")
        st.markdown("---")

        # API status
        if Config.is_gemini_configured():
            st.success("✅ Gemini API 已設定")
        else:
            st.warning("⚠️ 請設定 Gemini API Key")

        if Config.is_maps_configured():
            st.success("✅ Google Maps API 已設定")
        else:
            st.info("ℹ️ Google Maps API 未設定（地圖功能受限）")

        st.markdown("---")

        # Quick stats
        storage = ReceiptStorage()
        stats = storage.stats

        st.metric("📝 發票數量", stats["receipt_count"])
        st.metric("📦 品項數量", stats["item_count"])
        if stats["total_spending"] > 0:
            st.metric("💰 總消費", f"{stats['total_spending']:,.0f}")

    # Main content
    st.title("🧾 Trip Ledger AI")
    st.markdown("### AI 驅動的旅遊發票記帳工具")

    st.markdown("""
    歡迎使用 Trip Ledger AI！這是一個智慧型旅遊記帳工具，可以：

    - 📸 **辨識發票照片** - 自動擷取消費資訊
    - 📊 **視覺化分析** - 直觀的圖表與時間線
    - 🗺️ **地理分布** - 在地圖上查看消費地點
    - 📤 **匯出報告** - Excel、PDF 格式匯出
    """)

    st.markdown("---")

    # Quick actions
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📤 開始使用")
        st.markdown("上傳發票照片，讓 AI 自動辨識並記錄。")
        if st.button("前往上傳頁面", type="primary", key="goto_upload"):
            st.switch_page("pages/1_upload.py")

    with col2:
        st.markdown("### 📊 查看分析")
        st.markdown("查看消費類別統計與趨勢圖表。")
        if st.button("前往分析頁面", key="goto_analysis"):
            st.switch_page("pages/3_analysis.py")

    with col3:
        st.markdown("### ⚙️ 設定")
        st.markdown("配置 API Key 與應用程式設定。")
        if st.button("前往設定頁面", key="goto_settings"):
            st.switch_page("pages/5_settings.py")

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #888; font-size: 0.9em;">
            Made with ❤️ using Streamlit & Gemini 2.0 Flash
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
