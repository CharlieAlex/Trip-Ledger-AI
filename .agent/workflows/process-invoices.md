---
description: 批次處理發票照片並轉換為 CSV 資料
---

# 處理發票照片

將 `data/photos/` 目錄中的發票照片批次處理，擷取結構化資料並儲存為 CSV。

## 前置準備

1. 確認已設定 Gemini API Key（在 `.env` 檔案或 Streamlit 設定頁面）
2. 將發票照片放入 `data/photos/` 目錄

## 處理步驟

// turbo
1. 同步依賴：
```bash
make sync
```

// turbo
2. 執行發票擷取：
```bash
make extract
```

3. 若需強制重新處理（忽略快取）：
```bash
make extract-force
```

// turbo
4. 檢視產生的資料檔案：
```bash
ls -la data/
cat data/receipts.csv
```

## 輸出檔案

- `data/receipts.csv`：發票主檔（店家、時間、金額等）
- `data/items.csv`：品項明細（名稱、分類、價格等）
- `data/cache/processed.json`：處理快取

## 疑難排解

如遇到錯誤：
- 確認 API Key 是否正確設定
- 確認照片格式為支援的類型（jpg, png, heic）
- 檢查 `data/cache/` 中的快取記錄
