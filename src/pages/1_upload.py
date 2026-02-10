"""Upload page - Upload and process invoice photos."""

import streamlit as st
from pathlib import Path

from src.config import Config
from src.etl.storage import ReceiptStorage
from src.extractors.invoice_parser import InvoiceParser

st.set_page_config(
    page_title="上傳發票 | Trip Ledger AI",
    page_icon="📤",
    layout="wide",
)

st.title("📤 上傳發票照片")

# Check API configuration
if not Config.is_gemini_configured():
    st.error("⚠️ 請先設定 Gemini API Key")
    st.info("前往 設定 頁面配置 API Key")
    if st.button("前往設定"):
        st.switch_page("pages/5_settings.py")
    st.stop()

# File uploader
st.markdown("### 選擇發票照片")
st.markdown("支援格式：JPG, PNG, HEIC")

uploaded_files = st.file_uploader(
    "拖曳或選擇檔案",
    type=["jpg", "jpeg", "png", "heic", "heif"],
    accept_multiple_files=True,
    help="支援一次上傳多張照片",
)

if uploaded_files:
    st.markdown(f"**已選擇 {len(uploaded_files)} 個檔案**")

    # Display previews
    cols = st.columns(min(4, len(uploaded_files)))
    for i, uploaded_file in enumerate(uploaded_files[:4]):
        with cols[i]:
            st.image(uploaded_file, caption=uploaded_file.name, width='stretch')

    if len(uploaded_files) > 4:
        st.info(f"還有 {len(uploaded_files) - 4} 個檔案...")

    st.markdown("---")

    # Processing options
    col1, col2 = st.columns(2)
    with col1:
        force_reprocess = st.checkbox("強制重新處理", help="忽略快取，重新辨識所有照片")

    # Process button
    if st.button("🚀 開始處理", type="primary"):
        # Save uploaded files
        st.markdown("### 處理進度")

        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()

        # Save files to photos directory
        saved_paths = []
        for uploaded_file in uploaded_files:
            save_path = Config.PHOTOS_DIR / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            saved_paths.append(save_path)

        # Process files
        parser = InvoiceParser(force_reprocess=force_reprocess)
        storage = ReceiptStorage()

        results = []
        for i, file_path in enumerate(saved_paths):
            progress = (i + 1) / len(saved_paths)
            progress_bar.progress(progress)
            status_text.text(f"處理中: {file_path.name} ({i + 1}/{len(saved_paths)})")

            result = parser.process_image(file_path)
            results.append(result)

            # Save if successful
            if result.success and result.receipt:
                storage.save_receipt(result.receipt)

        progress_bar.progress(1.0)
        status_text.text("處理完成！")

        # Show results
        with results_container:
            st.markdown("### 處理結果")

            success_count = sum(1 for r in results if r.success and r.receipt)
            cached_count = sum(1 for r in results if r.success and not r.receipt)
            failed_count = sum(1 for r in results if not r.success)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("✅ 成功", success_count)
            with col2:
                st.metric("⏭️ 已快取", cached_count)
            with col3:
                st.metric("❌ 失敗", failed_count)

            # Details
            for result in results:
                if result.success and result.receipt:
                    receipt = result.receipt
                    with st.expander(f"✅ {receipt.store_name} - {receipt.total} {receipt.currency.value}"):
                        st.write(f"**日期時間**: {receipt.date} {receipt.time}")
                        st.write(f"**品項數量**: {len(receipt.items)}")
                        if receipt.items:
                            items_data = [
                                {
                                    "品項": item.name,
                                    "類別": f"{Config.get_category_emoji(item.category.value)} {Config.get_category_label(item.category.value)}",
                                    "金額": float(item.total_price),
                                }
                                for item in receipt.items
                            ]
                            st.dataframe(items_data, width='stretch')

                elif result.success:
                    st.info(f"⏭️ {Path(result.source_image).name} - 已快取")

                else:
                    st.error(f"❌ {Path(result.source_image).name} - {result.error_message}")

st.markdown("---")

# Show existing photos
st.markdown("### 📁 已上傳的照片")

photos = list(Config.PHOTOS_DIR.glob("*"))
photos = [p for p in photos if p.suffix.lower() in Config.SUPPORTED_IMAGE_EXTENSIONS]

if photos:
    st.markdown(f"共 {len(photos)} 張照片")

    # Display in grid
    cols = st.columns(6)
    for i, photo in enumerate(photos[:12]):
        with cols[i % 6]:
            try:
                st.image(str(photo), caption=photo.name, width='stretch')
            except Exception:
                st.text(photo.name)

    if len(photos) > 12:
        st.info(f"還有 {len(photos) - 12} 張照片...")
else:
    st.info("尚無已上傳的照片")
