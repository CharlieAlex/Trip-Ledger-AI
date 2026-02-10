# Trip Ledger AI 🧾

AI 驅動的旅遊發票記帳工具，使用 Gemini 2.0 Flash 自動辨識發票照片並進行視覺化分析。

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)
![Gemini](https://img.shields.io/badge/Gemini-2.0%20Flash-orange.svg)

## ✨ 功能特色

- 📸 **發票照片辨識** - 上傳發票照片，自動擷取消費資訊
- 🌍 **多語系支援** - 支援日文、英文、繁體中文發票
- 🏷️ **智慧分類** - 自動將品項分類到 8 大類別
- 📅 **時間線視覺化** - 按日期查看消費記錄
- 📊 **圖表分析** - 類別統計、每日趨勢、店家分析
- 🗺️ **地理分布** - 在地圖上查看消費地點
- 📤 **報告匯出** - Excel、PDF 格式報告

## 🚀 快速開始

### 1. 安裝依賴

```bash
# 使用 uv
uv sync
```

### 2. 設定 API Key

建立 `.env` 檔案：

```bash
cp .env.example .env
```

編輯 `.env`，填入你的 API Key：

```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here  # 可選，用於地圖功能
```

或在 Streamlit 應用程式的「設定」頁面中輸入。

### 3. 啟動應用程式

```bash
make run
```

或：

```bash
uv run streamlit run src/app.py
```

瀏覽器開啟 http://localhost:8501

## 📁 專案結構

```
Trip-Ledger-AI/
├── .agent/
│   ├── skills/                  # Agent Skills
│   │   ├── invoice-extractor/   # 發票辨識
│   │   ├── category-classifier/ # 品項分類
│   │   └── geocoder/            # 地理編碼
│   └── workflows/               # 工作流程
├── src/
│   ├── app.py                   # Streamlit 主入口
│   ├── config.py                # 設定管理
│   ├── extractors/              # 發票擷取模組
│   ├── etl/                     # 資料處理模組
│   ├── geo/                     # 地理功能
│   ├── visualization/           # 視覺化模組
│   └── pages/                   # Streamlit 頁面
├── data/
│   ├── photos/                  # 發票照片
│   ├── cache/                   # 處理快取
│   ├── receipts.csv             # 發票資料
│   └── items.csv                # 品項資料
├── exports/                     # 匯出報告
├── Makefile                     # 常用指令
├── pyproject.toml               # 專案設定
└── README.md
```

## 🛠️ 常用指令

```bash
make help          # 顯示所有可用指令
make sync          # 同步依賴
make run           # 啟動應用程式
make extract       # 處理發票照片
make extract-force # 強制重新處理
make export-excel  # 匯出 Excel 報告
make export-pdf    # 匯出 PDF 報告
make clean-cache   # 清除快取
make test          # 執行測試
```

## 🧠 Agent Skills

本專案包含三個可重複使用的 Agent Skills：

### Invoice Extractor

從發票照片中擷取結構化資料。

```bash
uv run python .agent/skills/invoice-extractor/scripts/extract.py
```

### Category Classifier

將商品品項自動分類。

```bash
uv run python .agent/skills/category-classifier/scripts/classify.py "商品名稱"
```

### Geocoder

將店家資訊轉換為地理座標。

```bash
uv run python .agent/skills/geocoder/scripts/geocode.py "店家名稱"
```

## 📊 支援的類別

| 類別 | Emoji | 說明 | 子類別範例 |
|------|-------|------|-----------|
| food | 🍔 | 食物 | meal, snack, groceries |
| beverage | 🥤 | 飲料 | coffee, alcohol, soft_drink |
| transport | 🚃 | 交通 | train, taxi, flight, fuel |
| lodging | 🏨 | 住宿 | hotel, hostel, airbnb |
| shopping | 🛍️ | 購物 | clothing, souvenir, electronics |
| entertainment | 🎢 | 娛樂 | ticket, activity, attraction |
| health | 💊 | 醫療 | pharmacy, medical |
| other | 📦 | 其他 | uncategorized |

## 💡 使用提示

1. **發票照片** - 確保照片清晰、光線充足
2. **一張一票** - 每張照片只包含一張發票最佳
3. **快取機制** - 相同照片不會重複處理，使用 `--force` 強制重新處理
4. **API 用量** - 每張發票約消耗 1000-2000 tokens

## 📄 授權

MIT License

---

Made with ❤️ using Streamlit & Gemini 2.0 Flash
