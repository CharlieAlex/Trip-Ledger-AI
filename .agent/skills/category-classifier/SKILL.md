---
name: Category Classifier
description: |
  使用 LLM 或規則引擎將商品品項智慧分類到預定義類別。
  支援多語系（日文、英文、繁體中文）商品名稱，並提供子類別分類。
version: "1.0.0"
author: Trip Ledger AI
---

# Category Classifier Skill

將商品品項自動分類到預定義類別的 Agent Skill。

## 功能

- **多語系支援**：識別日文、英文、繁體中文商品名稱
- **主類別分類**：將品項分類到 8 大類別
- **子類別分類**：進一步細分為具體類型
- **規則引擎**：使用關鍵字匹配作為快速分類方案

## 使用方式

### Python API

```python
from src.extractors.category_classifier import CategoryClassifier, classify_item

classifier = CategoryClassifier()

# 分類單一品項
category = classifier.classify("おにぎり 鮭")
print(category)  # Category.FOOD

# 取得子類別
subcategory = classifier.get_subcategory("コーヒー", Category.BEVERAGE)
print(subcategory)  # "coffee"

# 便利函數
category, subcategory = classify_item("新幹線切符")
print(f"{category}: {subcategory}")  # Category.TRANSPORT: train
```

## 類別定義

| 類別 | Emoji | 說明 | 子類別 |
|------|-------|------|--------|
| `food` | 🍔 | 食物 | meal, snack, groceries |
| `beverage` | 🥤 | 飲料 | coffee, alcohol, soft_drink |
| `transport` | 🚃 | 交通 | train, taxi, flight, fuel |
| `lodging` | 🏨 | 住宿 | hotel, hostel, airbnb |
| `shopping` | 🛍️ | 購物 | clothing, souvenir, electronics |
| `entertainment` | 🎢 | 娛樂 | ticket, activity, attraction |
| `health` | 💊 | 醫療 | pharmacy, medical |
| `other` | 📦 | 其他 | uncategorized |

## 實作細節

分類優先順序：
1. **LLM 分類**（在發票擷取時由 Gemini 完成）
2. **關鍵字匹配**（作為 fallback 或獨立使用）

關鍵字支援的語言：
- 日文（平假名、片假名、漢字）
- 英文
- 繁體中文

## 擴充類別

如需新增類別，請修改 `src/config.py` 中的 `CATEGORIES` 設定。
