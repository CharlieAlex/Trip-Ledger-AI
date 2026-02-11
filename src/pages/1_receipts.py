"""Receipt Manager - Upload, view, and manage receipts."""

import time
from pathlib import Path

import pandas as pd
import streamlit as st
from loguru import logger

from src.config import Config
from src.etl.cache import ProcessingCache
from src.etl.storage import ReceiptStorage
from src.extractors.image_preprocessor import get_image_hash
from src.extractors.invoice_parser import InvoiceParser

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

    # --- Section 1: Upload ---
    with st.expander("📤 上傳新發票", expanded=False):
        st.markdown("### 上傳照片")
        uploaded_files = st.file_uploader(
            "拖曳或選擇檔案",
            type=["jpg", "jpeg", "png", "heic", "heif"],
            accept_multiple_files=True,
            help="支援一次上傳多張照片",
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            force_reprocess = st.checkbox("強制重新處理", help="忽略快取，重新辨識所有照片")

        if uploaded_files:
            if st.button("🚀 開始處理", type="primary"):
                process_uploads(uploaded_files, force_reprocess)

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


def process_uploads(uploaded_files, force_reprocess):
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
    parser = InvoiceParser(force_reprocess=force_reprocess)
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
        title = f"{row['time']} - {row['store_name']}"
        if is_duplicate:
            st.markdown(f"**⚠️ 疑似重複: {title}**")
        else:
            st.markdown(f"**{title}**")

        # Amount
        st.markdown(f"💰 **{row['total']} {row['currency']}**")

        # Image (if exists)
        image_path = Path(Config.PHOTOS_DIR) / Path(row["source_image"]).name
        if image_path.exists():
            st.image(str(image_path), width=300)
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
        # Get items for this receipt
        items_df = storage.get_items_by_receipt(receipt_id)

        if len(items_df) > 0:
            # Prepare for editor
            edit_df = items_df.copy()

            # Category options
            categories = list(Config.CATEGORIES.keys())

            # Display editor
            edited_df = st.data_editor(
                edit_df,
                column_config={
                    "name": "品項名稱",
                    "unit_price": st.column_config.NumberColumn("單價", min_value=0, format="%.2f"),
                    "quantity": st.column_config.NumberColumn("數量", min_value=1, step=1),
                    "total_price": st.column_config.NumberColumn("總價", min_value=0, format="%.2f"),
                    "category": st.column_config.SelectboxColumn(
                        "類別",
                        options=categories,
                        required=True,
                    ),
                    "subcategory": st.column_config.TextColumn("子類別"),
                },
                hide_index=True,
                key=f"editor_{receipt_id}",
                disabled=["item_id", "receipt_id", "name_translated"],
                column_order=["name", "category", "subcategory", "unit_price", "quantity", "total_price"]
            )

            if st.button("💾 儲存修改", key=f"save_{receipt_id}"):
                # Recalculate totals based on edited values (optional validation)
                # For now assume user input is correct, or we can force calc
                edited_df["total_price"] = edited_df["unit_price"] * edited_df["quantity"]

                if storage.update_items(receipt_id, edited_df):
                    st.success("✅ 已儲存")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ 儲存失敗")
        else:
            st.info("此發票無品項資料")


def reprocess_receipt(source_image):
    """Reprocess a single receipt."""
    file_path = Config.PHOTOS_DIR / Path(source_image).name
    if not file_path.exists():
        st.error(f"找不到檔案: {file_path}")
        return

    with st.spinner("重新處理中..."):
        parser = InvoiceParser(force_reprocess=True)
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
