---
name: Geocoder
description: |
  使用 Google Maps API 將店家名稱或地址轉換為經緯度座標。
  支援快取機制避免重複查詢，可與 MCP 整合。
version: "1.0.0"
author: Trip Ledger AI
---

# Geocoder Skill

將店家資訊轉換為地理座標的 Agent Skill。

## 功能

- **地理編碼**：將地址或店家名稱轉換為經緯度
- **快取機制**：避免重複 API 查詢
- **MCP 整合**：可透過 Google Maps MCP 進行查詢
- **批次處理**：支援批次更新多筆發票的座標

## 使用方式

### Python API

```python
from src.geo.geocoder import Geocoder

geocoder = Geocoder()

# 查詢單一地點
result = geocoder.geocode("ローソン 渋谷店", region="japan")
if result:
    print(f"座標: {result.latitude}, {result.longitude}")
    print(f"地址: {result.formatted_address}")

# 為發票批次新增座標
geocoder.geocode_receipts()
```

### CLI

```bash
# 查詢單一地點
uv run python .agent/skills/geocoder/scripts/geocode.py "東京駅"

# 批次更新發票座標
uv run python .agent/skills/geocoder/scripts/geocode.py --update-receipts
```

## 輸出格式

```json
{
  "latitude": 35.6812,
  "longitude": 139.7671,
  "formatted_address": "日本、〒100-0005 東京都千代田区丸の内１丁目",
  "place_id": "ChIJC3Cf2PuLGGARx..."
}
```

## 環境需求

需設定以下環境變數：

```bash
GOOGLE_MAPS_API_KEY=your_api_key_here
```

## MCP 整合

此 Skill 設計為可與 Google Maps MCP 整合。當有 MCP 可用時，將優先使用 MCP 進行地理編碼查詢。

## 費用考量

Google Maps Geocoding API 費用：
- 每 1000 次查詢約 $5 USD
- 建議使用快取機制減少查詢次數
- 發票資料中相同店家會自動使用快取
