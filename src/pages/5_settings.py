"""Settings page - API configuration and app preferences."""


import re

import streamlit as st

from src.config import Config
from src.etl.exporter import ReportExporter
from src.ui.sidebar import render_sidebar

st.set_page_config(
    page_title="設定 | Trip Ledger AI",
    page_icon="⚙️",
    layout="wide",
)

st.title("⚙️ 設定")

render_sidebar()

# Language Settings
st.markdown("### 🌐 語言設定")
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        primary_lang = st.text_input(
            "主要語言 (翻譯目標)",
            value=Config.PRIMARY_LANGUAGE,
            help="AI 將把發票內容翻譯成此語言 (例如: Traditional Chinese)"
        )
    with col2:
        dest_lang = st.text_input(
            "旅遊地語言 (原文)",
            value=Config.DESTINATION_LANGUAGE,
            help="發票的主要語言 (例如: Japanese)"
        )

    if st.button("💾 儲存語言設定"):
        Config.set_language_settings(primary_lang, dest_lang)
        env_path = Config.PROJECT_ROOT / ".env"
        env_content = ""
        if env_path.exists():
            env_content = env_path.read_text()

        # Helper to update env var in string
        def update_env_str(content, key, value):
            pattern = re.compile(f"^{key}=.*$", re.MULTILINE)
            if pattern.search(content):
                return pattern.sub(f"{key}={value}", content)
            else:
                return content + f"\n{key}={value}\n"

        env_content = update_env_str(env_content, "PRIMARY_LANGUAGE", primary_lang)
        env_content = update_env_str(env_content, "DESTINATION_LANGUAGE", dest_lang)

        env_path.write_text(env_content)
        st.success(f"✅ 語言設定已更新: {dest_lang} -> {primary_lang}")

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

# with st.expander("Google Maps API", expanded=False):
#     st.markdown("""
#     Google Maps API 用於地理編碼（取得店家座標）。
#     [取得 API Key](https://console.cloud.google.com/apis/credentials)

#     需啟用 Geocoding API。
#     """)

#     maps_key = st.text_input(
#         "Google Maps API Key",
#         value=Config.GOOGLE_MAPS_API_KEY or "",
#         type="password",
#         help="輸入你的 Google Maps API Key",
#     )

#     if st.button("儲存 Google Maps API Key"):
#         if maps_key:
#             Config.set_google_maps_api_key(maps_key)
#             # Also save to .env file
#             env_path = Config.PROJECT_ROOT / ".env"
#             env_content = ""
#             if env_path.exists():
#                 env_content = env_path.read_text()
#                 import re
#                 if "GOOGLE_MAPS_API_KEY=" in env_content:
#                     env_content = re.sub(r"GOOGLE_MAPS_API_KEY=.*\n?", f"GOOGLE_MAPS_API_KEY={maps_key}\n", env_content)  # noqa: E501
#                 else:
#                     env_content += f"\nGOOGLE_MAPS_API_KEY={maps_key}\n"
#             else:
#                 env_content = f"GOOGLE_MAPS_API_KEY={maps_key}\n"
#             env_path.write_text(env_content)
#             st.success("✅ Google Maps API Key 已儲存")
#         else:
#             st.error("請輸入 API Key")

#     if Config.is_maps_configured():
#         st.success("✅ 已設定")
#     else:
#         st.info("ℹ️ 未設定（地圖功能受限）")

st.markdown("---")

# Category Management
st.markdown("### 🏷️ 類別管理")

with st.expander("編輯類別與子類別", expanded=False):
    # Select category to edit
    category_keys = list(Config.CATEGORIES.keys())
    # Map labels for display
    cat_options = {k: f"{Config.get_category_emoji(k)} {Config.get_category_label(k)}" for k in category_keys}

    selected_key = st.selectbox(
        "選擇要編輯的類別",
        options=category_keys,
        format_func=lambda x: cat_options[x]
    )

    if selected_key:
        current_data = Config.CATEGORIES[selected_key]

        col1, col2 = st.columns([1, 3])
        with col1:
            new_emoji = st.text_input("Emoji", value=current_data.get("emoji", ""))
        with col2:
            new_label = st.text_input("顯示名稱", value=current_data.get("label", ""))

        # Subcategories editor
        current_subs = current_data.get("subcategories", [])
        # Convert to dataframe for editor
        import pandas as pd
        sub_df = pd.DataFrame({"子類別": current_subs})

        st.markdown("#### 子類別列表")
        edited_sub_df = st.data_editor(
            sub_df,
            num_rows="dynamic",
            width='stretch',
            hide_index=True,
            key=f"sub_edit_{selected_key}"
        )

        if st.button("💾 儲存變更"):
            # Update config object
            updated_subs = [x for x in edited_sub_df["子類別"].tolist() if x and x.strip()]

            Config.CATEGORIES[selected_key]["emoji"] = new_emoji
            Config.CATEGORIES[selected_key]["label"] = new_label
            Config.CATEGORIES[selected_key]["subcategories"] = updated_subs

            # Save to file
            Config.save_categories(Config.CATEGORIES)
            st.success("✅ 類別設定已儲存")
            st.rerun()

    st.markdown("---")
    if st.button("⚠️ 重置為預設值", help="將所有類別設定還原為系統預設值"):
        # Default categories
        defaults = {
            "food": {
                "emoji": "🍔",
                "label": "食物",
                "subcategories": ["正餐", "點心", "食材/雜貨", "早餐", "午餐", "晚餐", "飲料"]
            },
            "transport": {
                "emoji": "🚃",
                "label": "交通",
                "subcategories": ["電車/地鐵", "計程車/Uber", "機票", "租車/加油", "巴士", "新幹線"]
            },
            "lodging": {
                "emoji": "🏨",
                "label": "住宿",
                "subcategories": ["飯店", "民宿/Airbnb", "溫泉旅館"]
            },
            "shopping": {
                "emoji": "🛍️",
                "label": "購物",
                "subcategories": ["生活用品", "衣服/飾品", "伴手禮(食)", "伴手禮(玩)", "藥妝", "電器", "雜貨"]
            },
            "entertainment": {
                "emoji": "🎢",
                "label": "娛樂",
                "subcategories": ["門票", "體驗活動", "展覽", "遊戲"]
            },
            "health": {
                "emoji": "💊",
                "label": "醫療",
                "subcategories": ["藥品", "看診"]
            },
            "other": {
                "emoji": "📦",
                "label": "其他",
                "subcategories": ["未分類", "服務費", "稅金"]
            }
        }
        Config.save_categories(defaults)
        st.success("✅ 已重置為預設值")
        st.rerun()

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
