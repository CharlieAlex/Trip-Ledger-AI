"""Settings page - API configuration and app preferences."""


import streamlit as st

from src.config import Config
from src.etl.exporter import ReportExporter

st.set_page_config(
    page_title="設定 | Trip Ledger AI",
    page_icon="⚙️",
    layout="wide",
)

st.title("⚙️ 設定")

# API Configuration
st.markdown("### 🔑 API 設定")

with st.expander("Gemini API", expanded=not Config.is_gemini_configured()):
    st.markdown("""
    Gemini API 用於發票照片辨識。
    [取得 API Key](https://aistudio.google.com/apikey)
    """)

    gemini_key = st.text_input(
        "Gemini API Key",
        value=Config.GEMINI_API_KEY or "",
        type="password",
        help="輸入你的 Gemini API Key",
    )

    if st.button("儲存 Gemini API Key"):
        if gemini_key:
            Config.set_gemini_api_key(gemini_key)
            # Also save to .env file
            env_path = Config.PROJECT_ROOT / ".env"
            env_content = ""
            if env_path.exists():
                env_content = env_path.read_text()
                # Replace existing key
                import re
                if "GEMINI_API_KEY=" in env_content:
                    env_content = re.sub(r"GEMINI_API_KEY=.*\n?", f"GEMINI_API_KEY={gemini_key}\n", env_content)
                else:
                    env_content += f"\nGEMINI_API_KEY={gemini_key}\n"
            else:
                env_content = f"GEMINI_API_KEY={gemini_key}\n"
            env_path.write_text(env_content)
            st.success("✅ Gemini API Key 已儲存")
        else:
            st.error("請輸入 API Key")

    if Config.is_gemini_configured():
        st.success("✅ 已設定")
    else:
        st.warning("⚠️ 未設定")

with st.expander("Google Maps API", expanded=False):
    st.markdown("""
    Google Maps API 用於地理編碼（取得店家座標）。
    [取得 API Key](https://console.cloud.google.com/apis/credentials)

    需啟用 Geocoding API。
    """)

    maps_key = st.text_input(
        "Google Maps API Key",
        value=Config.GOOGLE_MAPS_API_KEY or "",
        type="password",
        help="輸入你的 Google Maps API Key",
    )

    if st.button("儲存 Google Maps API Key"):
        if maps_key:
            Config.set_google_maps_api_key(maps_key)
            # Also save to .env file
            env_path = Config.PROJECT_ROOT / ".env"
            env_content = ""
            if env_path.exists():
                env_content = env_path.read_text()
                import re
                if "GOOGLE_MAPS_API_KEY=" in env_content:
                    env_content = re.sub(r"GOOGLE_MAPS_API_KEY=.*\n?", f"GOOGLE_MAPS_API_KEY={maps_key}\n", env_content)
                else:
                    env_content += f"\nGOOGLE_MAPS_API_KEY={maps_key}\n"
            else:
                env_content = f"GOOGLE_MAPS_API_KEY={maps_key}\n"
            env_path.write_text(env_content)
            st.success("✅ Google Maps API Key 已儲存")
        else:
            st.error("請輸入 API Key")

    if Config.is_maps_configured():
        st.success("✅ 已設定")
    else:
        st.info("ℹ️ 未設定（地圖功能受限）")

st.markdown("---")


# Export
st.markdown("### 📤 匯出報告")

col1, col2, col3 = st.columns(3)

exporter = ReportExporter()

with col1:
    if st.button("📊 匯出 Excel"):
        try:
            path = exporter.export_excel()
            st.success(f"已匯出: {path.name}")
            with open(path, "rb") as f:
                st.download_button(
                    "📥 下載 Excel",
                    f.read(),
                    path.name,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        except Exception as e:
            st.error(f"匯出失敗: {e}")

with col2:
    if st.button("📄 匯出 PDF"):
        try:
            path = exporter.export_pdf()
            st.success(f"已匯出: {path.name}")
            with open(path, "rb") as f:
                st.download_button(
                    "📥 下載 PDF",
                    f.read(),
                    path.name,
                    "application/pdf",
                )
        except Exception as e:
            st.error(f"匯出失敗: {e}")

with col3:
    if st.button("📋 產生分享文字"):
        text = exporter.generate_share_link()
        st.text_area("分享內容", text, height=300)
        st.button("📋 複製到剪貼簿", disabled=True, help="請手動選取並複製")

st.markdown("---")

# About
st.markdown("### ℹ️ 關於")
st.markdown("""
**Trip Ledger AI** v0.1.0

AI 驅動的旅遊發票記帳工具，使用 Gemini 2.0 Flash 進行發票辨識。

- 📸 支援多語系發票辨識（日文、英文、繁體中文）
- 🏷️ 自動品項分類
- 📊 視覺化消費分析
- 🗺️ 地理分布地圖
- 📤 Excel/PDF 報告匯出
""")
