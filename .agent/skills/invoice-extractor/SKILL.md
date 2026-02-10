---
name: Invoice Extractor
description: |
  使用 Gemini 2.0 Flash API 從發票/收據照片中擷取結構化消費資料。
  支援多語系（繁體中文、日文、英文），自動偵測語言並轉換為統一 JSON 格式。
version: "1.0.0"
author: Trip Ledger AI
---

# Invoice Extractor Skill

從發票照片中擷取結構化消費資料的 Agent Skill。

## 功能

- **多語系辨識**：支援繁體中文、日文、英文發票
- **結構化輸出**：將發票內容轉換為標準化 JSON 格式
- **品項分類**：自動將每個品項分類到預設類別
- **快取支援**：避免重複處理相同發票

## 使用方式

### 方式一：命令列

```bash
# 處理 data/photos/ 目錄下的所有照片
uv run python .agent/skills/invoice-extractor/scripts/extract.py

# 處理單一檔案
uv run python .agent/skills/invoice-extractor/scripts/extract.py --file path/to/invoice.jpg

# 強制重新處理（忽略快取）
uv run python .agent/skills/invoice-extractor/scripts/extract.py --force
```

### 方式二：Python API

```python
from src.extractors.invoice_parser import InvoiceParser

parser = InvoiceParser()

# 處理單一圖片
result = parser.process_image("path/to/invoice.jpg")

if result.success:
    receipt = result.receipt
    print(f"店家: {receipt.store_name}")
    print(f"金額: {receipt.total} {receipt.currency}")
    for item in receipt.items:
        print(f"  - {item.name}: {item.total_price}")
else:
    print(f"處理失敗: {result.error_message}")
```

## 輸入參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `image_path` | string | 是 | 發票照片路徑，支援 jpg/png/heic |
| `force_reprocess` | boolean | 否 | 設為 true 則忽略快取強制重新處理 |

## 輸出格式

### Receipt（發票）

```json
{
  "receipt_id": "a1b2c3d4...",
  "timestamp": "2024-01-15T14:30:00",
  "store_name": "ローソン 渋谷店",
  "store_name_translated": "Lawson 澀谷店",
  "store_address": "東京都渋谷区...",
  "items": [...],
  "subtotal": 463,
  "tax": 37,
  "total": 500,
  "currency": "JPY",
  "original_language": "ja",
  "source_image": "invoice_001.jpg"
}
```

### Item（品項）

```json
{
  "item_id": "item_001",
  "receipt_id": "a1b2c3d4...",
  "name": "おにぎり 鮭",
  "name_translated": "飯糰 鮭魚",
  "quantity": 2,
  "unit_price": 130,
  "total_price": 260,
  "category": "food",
  "subcategory": "snack"
}
```

## 支援的類別

| 類別 | Emoji | 說明 | 子類別範例 |
|------|-------|------|-----------|
| `food` | 🍔 | 食物 | meal, snack, groceries |
| `beverage` | 🥤 | 飲料 | coffee, alcohol, soft_drink |
| `transport` | 🚃 | 交通 | train, taxi, flight, fuel |
| `lodging` | 🏨 | 住宿 | hotel, hostel, airbnb |
| `shopping` | 🛍️ | 購物 | clothing, souvenir, electronics |
| `entertainment` | 🎢 | 娛樂 | ticket, activity, attraction |
| `health` | 💊 | 醫療 | pharmacy, medical |
| `other` | 📦 | 其他 | uncategorized |

## 環境需求

需設定以下環境變數：

```bash
GEMINI_API_KEY=your_api_key_here
```

可在 `.env` 檔案中設定，或透過 Streamlit UI 設定。

## 範例

查看 `examples/` 目錄中的範例輸入輸出：

- `sample_input.jpg` - 範例發票照片（日文）
- `sample_output.json` - 對應的處理結果

## 注意事項

1. **照片品質**：清晰的照片能提高辨識準確度
2. **多張發票**：每張照片應只包含一張發票
3. **API 用量**：每張照片約消耗 1000-2000 tokens
4. **快取**：預設會快取處理結果，相同照片不會重複處理
