"""Receipt Manager - Upload, view, and manage receipts."""

import io
import time
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF
import pandas as pd
import streamlit as st
from loguru import logger
from PIL import Image

from src.config import Config
from src.etl.cache import ProcessingCache
from src.etl.storage import ReceiptStorage
from src.extractors.image_preprocessor import get_image_hash
from src.extractors.invoice_parser import InvoiceParser
from src.ui.sidebar import render_sidebar

st.set_page_config(
    page_title="發票管理 | Trip Ledger AI",
    page_icon="🧾",
    layout="wide",
)

st.title("🧾 發票管理")

# Check API configuration
if not Config.is_gemini_configured():
    st.error("⚠️ 請先設定 Gemini API Key")
    st.info("前往 設定 頁面配置 API Key")
    if st.button("前往設定"):
        st.switch_page("pages/5_settings.py")
    st.stop()


def main():
    """Main function for Receipt Manager."""
    # Initialize storage and cache
    storage = ReceiptStorage()
    cache = ProcessingCache()

    # Initialize session state for processed images and sources
    if "processed_images" not in st.session_state:
        st.session_state.processed_images = {}
    if "processed_sources" not in st.session_state:
        st.session_state.processed_sources = set()

    render_sidebar()

    # --- Section 1: Upload ---
    with st.expander("📤 上傳新發票", expanded=True):
        st.markdown("### 1. 上傳照片")
        uploaded_files = st.file_uploader(
            "拖曳或選擇檔案",
            type=["jpg", "jpeg", "png", "heic", "heif", "pdf"],
            accept_multiple_files=True,
            help="支援一次上傳多張照片或 PDF",
            key="upload_uploader"
        )

        # Handle file upload changes
        _handle_file_upload_changes(uploaded_files)

        # Handle image preview and processing
        if st.session_state.processed_images:
            _handle_image_preview_and_processing(uploaded_files)

    st.divider()

    # --- Section 2: Receipt Gallery ---
    st.markdown("### 📋 發票列表")

    # Load data
    receipts_df = storage.load_receipts()
    duplicates = storage.find_duplicates()

    if len(receipts_df) == 0:
        st.info("尚無發票資料。請先上傳照片。")
    else:
        # Group by date
        dates = sorted(receipts_df["date"].unique(), reverse=True)

        for date in dates:
            date_receipts = receipts_df[receipts_df["date"] == date].sort_values("time", ascending=False)

            with st.expander(f"📅 {date} ({len(date_receipts)} 張)", expanded=True):
                # Grid layout
                cols = st.columns(3)

                for idx, (_, row) in enumerate(date_receipts.iterrows()):
                    with cols[idx % 3]:
                        display_receipt_card(row, storage, cache, duplicates)

    st.divider()

    # --- Section 3: Data Management ---
    with st.expander("🗑️ 資料管理"):
        st.warning("⚠️ 危險區域")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("清除快取 (Cache)", help="刪除所有 API 回應快取，下次處理需重新呼叫 API"):
                cache.clear()
                st.success("✅ 快取已清除")

        with col2:
            if st.button("清除所有資料", type="primary", help="刪除所有發票、CSV 與照片檔案"):
                confirm_clear_data()


def resize_image_bytes(image_bytes, max_long_side=768):
    """Resize image bytes to fit within max_long_side.

    Args:
        image_bytes (bytes): The original image bytes.
        max_long_side (int): The maximum length for the long side of the image.

    Returns:
        bytes: The resized image bytes (or original if smaller/error).
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size

        # Check if resize is needed
        if max(width, height) <= max_long_side:
            return image_bytes

        # Calculate new dimensions
        ratio = max_long_side / max(width, height)
        new_size = (int(width * ratio), int(height * ratio))

        # Resize
        image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Save to bytes
        buf = io.BytesIO()
        # Preserve format if possible, default to JPEG
        fmt = image.format if image.format else "JPEG"
        image.save(buf, format=fmt, quality=85)
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Resize failed: {e}")
        return image_bytes


def _handle_file_upload_changes(uploaded_files):
    """Handle file upload changes and conversion."""
    current_filenames = {f.name for f in uploaded_files}
    processed_sources = st.session_state.processed_sources

    if current_filenames == processed_sources:
        return

    st.info("偵測到新上傳檔案，請點擊下方按鈕進行縮圖處理。")

    if st.button("🔄 轉換圖片大小 (Resize Images)", type="primary"):
        _resize_uploaded_images(uploaded_files)


def _resize_uploaded_images(uploaded_files):
    """Resize all uploaded images, handling PDFs by splitting them."""
    st.session_state.processed_images = {}
    st.session_state.processed_sources = set()

    progress_text = st.empty()
    progress_bar = st.progress(0)

    total_files = len(uploaded_files)

    for i, uploaded_file in enumerate(uploaded_files):
        progress_text.text(f"正在處理: {uploaded_file.name}")
        file_bytes = uploaded_file.getvalue()
        file_type = uploaded_file.type

        # Handle PDF
        if file_type == "application/pdf" or uploaded_file.name.lower().endswith(".pdf"):
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap()
                    img_bytes = pix.tobytes("png")

                    page_name = f"{uploaded_file.name}_page_{page_num+1}.png"
                    resized_data = resize_image_bytes(img_bytes, 768)

                    st.session_state.processed_images[page_name] = {
                        "original": img_bytes,
                        "resized": resized_data,
                        "current_max": 768,
                        "type": "image/png"
                    }
                doc.close()
            except Exception as e:
                logger.error(f"Failed to process PDF {uploaded_file.name}: {e}")
                st.error(f"PDF 處理失敗: {uploaded_file.name}")

        # Handle Image
        else:
            resized_data = resize_image_bytes(file_bytes, 768)
            st.session_state.processed_images[uploaded_file.name] = {
                "original": file_bytes,
                "resized": resized_data,
                "current_max": 768,
                "type": uploaded_file.type
            }

        # Mark source as processed
        st.session_state.processed_sources.add(uploaded_file.name)
        progress_bar.progress((i + 1) / total_files)

    progress_text.empty()
    progress_bar.empty()
    st.rerun()


def _handle_image_preview_and_processing(uploaded_files):
    """Handle image preview, adjustment and processing."""
    st.divider()
    st.markdown("### 2. 預覽與調整 (Preview & Adjust)")

    # We display everything in processed_images
    # Note: uploaded_files might not 1:1 match processed_images due to PDF splitting
    # So we just show all processed_images

    # Check if we have orphaned images (source file removed)
    current_filenames = {f.name for f in uploaded_files}

    # Simple check: if processed_sources doesn't match current uploads, warn user
    if st.session_state.processed_sources != current_filenames:
        st.warning("⚠️ 檔案列表已變更，建議重新轉換圖片。")

    _render_image_previews()

    st.divider()
    if st.button("🚀 開始處理 (Start Processing)", type="primary"):
        _process_final_images()


def _render_image_previews():
    """Render image previews with adjustment controls."""
    cols = st.columns(5)

    # Sort keys for consistent display
    image_names = sorted(st.session_state.processed_images.keys())

    for idx, name in enumerate(image_names):
        file_data = st.session_state.processed_images[name]

        with cols[idx % 3]:
            st.image(file_data["resized"], caption=name, width='stretch')
            _render_image_controls(idx, name, file_data)


def _render_image_controls(idx, name, file_data):
    """Render controls for individual image adjustment."""
    c1, c2 = st.columns(2)

    with c1:
        if st.button("⏪ 還原", key=f"rest_{idx}_{name}"):
            file_data["resized"] = file_data["original"]
            file_data["current_max"] = 0  # 0 means original/no resize logic
            st.rerun()

    with c2:
        new_max = st.number_input(
            "長邊 (px)",
            value=file_data["current_max"] if file_data["current_max"] > 0 else 768,
            key=f"dim_{idx}_{name}"
        )
        if st.button("套用", key=f"apply_{idx}_{name}"):
            file_data["resized"] = resize_image_bytes(file_data["original"], int(new_max))
            file_data["current_max"] = int(new_max)
            st.rerun()


def _process_final_images():
    """Process final images and clean up session state."""
    final_files = []

    for name, data in st.session_state.processed_images.items():
        processed = _create_processed_file(name, data)
        final_files.append(processed)

    process_uploads(final_files)

    # Clear session state
    st.session_state.processed_images = {}
    st.session_state.processed_sources = set()
    st.session_state.manual_edit_mode = False
    st.rerun()


def _create_processed_file(name, file_data):
    """Create a ProcessedFile object from file data."""
    class ProcessedFile:
        def __init__(self, name, data, type):
            self.name = name
            self.data = data
            self.type = type

        def getbuffer(self):
            return self.data

        def getvalue(self):
            return self.data

    return ProcessedFile(
        name,
        file_data["resized"],
        file_data["type"]
    )


def process_uploads(uploaded_files):
    """Handle file uploads and processing."""
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Save files
    saved_paths = []
    for uploaded_file in uploaded_files:
        save_path = Config.PHOTOS_DIR / uploaded_file.name
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        saved_paths.append(save_path)

    # Process
    parser = InvoiceParser()
    storage = ReceiptStorage()

    success_count = 0

    for i, file_path in enumerate(saved_paths):
        progress = (i + 1) / len(saved_paths)
        progress_bar.progress(progress)
        status_text.text(f"處理中: {file_path.name}")

        result = parser.process_image(file_path)
        if result.success and result.receipt:
            storage.save_receipt(result.receipt)
            success_count += 1

    progress_bar.progress(1.0)
    status_text.text("處理完成！")

    if success_count > 0:
        st.success(f"成功處理 {success_count} 張發票")
        time.sleep(1)
        st.rerun()
    else:
        st.warning("沒有產生新的發票資料 (可能已存在或失敗)")


def display_receipt_card(row, storage, cache, duplicates):
    """Display a single receipt card."""
    receipt_id = row["receipt_id"]
    is_duplicate = False

    # Check for duplicates
    for dup_ids in duplicates.values():
        if receipt_id in dup_ids and len(dup_ids) > 1:
            is_duplicate = True
            break

    container = st.container(border=True)
    with container:
        # Header with warning if duplicate
        # Display name based on settings
        show_translated = st.session_state.get("show_translated", True)
        display_name = (row["store_name_translated"]
            if show_translated and pd.notna(row["store_name_translated"]) and row["store_name_translated"]
            else row["store_name"]
        )

        title = f"{row['time']} - {display_name}"
        if is_duplicate:
            st.markdown(f"**⚠️ 疑似重複: {title}**")
        else:
            st.markdown(f"**{title}**")

        # Amount
        st.markdown(f"💰 **{row['total']} {row['currency']}**")

        # Image (if exists)
        image_path = Path(Config.PHOTOS_DIR) / Path(row["source_image"]).name
        if image_path.exists():
            st.image(str(image_path), width='stretch')
        else:
            st.text("照片遺失")

        # Actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 重跑", key=f"reproc_{receipt_id}", help="重新辨識此張發票"):
                reprocess_receipt(row["source_image"])

        with col2:
            if st.button("🗑️ 刪除", key=f"del_{receipt_id}", type="primary"):
                delete_receipt(receipt_id, row["source_image"], storage, cache)

    # Expanded details for editing
    with st.expander("📝 編輯明細", expanded=False):
        # Date and Time Editor
        col_date, col_time = st.columns(2)

        current_date_obj = pd.to_datetime(row["date"]).date()

        # Parse current time
        current_time_obj = datetime.now().time()
        if pd.notna(row["time"]) and row["time"]:
            try:
                if len(str(row["time"])) == 5:
                    current_time_obj = datetime.strptime(str(row["time"]), "%H:%M").time()
                elif len(str(row["time"])) >= 8:
                    current_time_obj = datetime.strptime(str(row["time"])[:8], "%H:%M:%S").time()
            except ValueError:
                pass

        with col_date:
            new_date = st.date_input(
                "日期",
                value=current_date_obj,
                min_value=pd.to_datetime("1900-01-01").date(),
                max_value=pd.to_datetime("2100-12-31").date(),
                key=f"date_{receipt_id}"
            )

        with col_time:
            new_time = st.time_input(
                "時間",
                value=current_time_obj,
                key=f"time_{receipt_id}"
            )

        # Get items for this receipt
        items_df = storage.get_items_by_receipt(receipt_id)

        if len(items_df) > 0:
            # Prepare for editor
            edit_df = items_df.copy()

            # Helper for display name
            show_translated = st.session_state.get("show_translated", True)

            if show_translated:
                # Use translated name if available, else original
                edit_df["display_name"] = edit_df.apply(
                    lambda x: x["name_translated"]
                    if pd.notna(x["name_translated"]) and x["name_translated"]
                    else x["name"],
                    axis=1,
                )
            else:
                edit_df["display_name"] = edit_df["name"]

            # Category options
            categories = list(Config.CATEGORIES.keys())

            # Display editor
            edited_df = st.data_editor(
                edit_df,
                column_config={
                    "display_name": "品項名稱 (顯示)",
                    "name": "品項名稱 (原文)",
                    "name_translated": "品項名稱 (翻譯)",
                    "unit_price": st.column_config.NumberColumn(
                        "單價", min_value=0, format="%.2f"
                    ),
                    "quantity": st.column_config.NumberColumn(
                        "數量", min_value=1, step=1
                    ),
                    "total_price": st.column_config.NumberColumn(
                        "總價", min_value=0, format="%.2f"
                    ),
                    "category": st.column_config.SelectboxColumn(
                        "類別",
                        options=categories,
                        required=True,
                    ),
                    "subcategory": st.column_config.TextColumn("子類別"),
                },
                hide_index=True,
                key=f"editor_{receipt_id}",
                # allow editing name (original) and name_translated
                disabled=["item_id", "receipt_id", "display_name"],
                column_order=[
                    "display_name",
                    "name",
                    "name_translated",
                    "category",
                    "subcategory",
                    "unit_price",
                    "quantity",
                    "total_price",
                ],
            )

            if st.button("💾 儲存修改", key=f"save_{receipt_id}"):
                # Recalculate totals based on edited values (optional validation)
                # For now assume user input is correct, or we can force calc
                edited_df["total_price"] = (
                    edited_df["unit_price"] * edited_df["quantity"]
                )

                # We need to drop our helper column before saving
                save_df = edited_df.drop(columns=["display_name"])

                items_updated = storage.update_items(receipt_id, save_df)

                # Update date/time if changed
                meta_updated = False
                if new_date != current_date_obj or new_time != current_time_obj:
                    new_timestamp = datetime.combine(new_date, new_time)
                    meta_updated = storage.update_receipt(
                        receipt_id,
                        {
                            "date": new_date.isoformat(),
                            "time": new_time.strftime("%H:%M:%S"),
                            "timestamp": new_timestamp.isoformat()
                        }
                    )

                if items_updated or meta_updated:
                    st.success("✅ 已儲存")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ 儲存失敗 (無變更或錯誤)")
        else:
            st.info("此發票無品項資料")

            # Allow saving date/time even if no items
            if st.button("💾 儲存修改", key=f"save_noitems_{receipt_id}"):
                if new_date != current_date_obj or new_time != current_time_obj:
                    new_timestamp = datetime.combine(new_date, new_time)
                    if storage.update_receipt(
                        receipt_id,
                        {
                            "date": new_date.isoformat(),
                            "time": new_time.strftime("%H:%M:%S"),
                            "timestamp": new_timestamp.isoformat()
                        }
                    ):
                        st.success("✅ 日期/時間已更新")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 更新失敗")


def reprocess_receipt(source_image):
    """Reprocess a single receipt."""
    file_path = Config.PHOTOS_DIR / Path(source_image).name
    if not file_path.exists():
        st.error(f"找不到檔案: {file_path}")
        return

    with st.spinner("重新處理中..."):
        # Clear cache for this file so parser will re-process it
        cache = ProcessingCache()
        file_hash = get_image_hash(file_path)
        cache.remove(file_hash)

        parser = InvoiceParser()
        storage = ReceiptStorage()

        result = parser.process_image(file_path)
        if result.success and result.receipt:
            storage.save_receipt(result.receipt)
            st.success("更新成功！")
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"處理失敗: {result.error_message}")


def delete_receipt(receipt_id, source_image, storage, cache):
    """Delete a receipt."""
    # Delete from CSV
    storage.delete_receipt(receipt_id)

    # Remove from cache (need hash)
    # Since we don't have hash easily, we might need to iterate or just ignore
    # Ideally storage should return hash or we re-calculate it
    file_path = Config.PHOTOS_DIR / Path(source_image).name
    if file_path.exists():
        file_hash = get_image_hash(file_path)
        cache.remove(file_hash)

        # Delete file
        try:
            file_path.unlink()
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")

    st.success("已刪除")
    time.sleep(0.5)
    st.rerun()


def confirm_clear_data():
    """Clear all data."""
    # This acts as a confirmation dialog
    if st.checkbox("確認刪除所有發票與照片？此動作無法復原。"):
        if st.button("💥 執行徹底清除", type="primary"):

            # Clear storage
            storage = ReceiptStorage()
            # Re-init csvs
            pd.DataFrame(columns=storage.RECEIPT_COLUMNS).to_csv(storage.receipts_file, index=False)
            pd.DataFrame(columns=storage.ITEM_COLUMNS).to_csv(storage.items_file, index=False)

            # Clear cache
            cache = ProcessingCache()
            cache.clear()

            # Clear photos
            if Config.PHOTOS_DIR.exists():
                for f in Config.PHOTOS_DIR.glob("*"):
                    if f.is_file():
                        f.unlink()

            st.success("所有資料已清除")
            time.sleep(1)
            st.rerun()


if __name__ == "__main__":
    main()
