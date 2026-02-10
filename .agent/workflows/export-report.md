---
description: 匯出分析報告為 Excel 或 PDF 格式
---

# 匯出報告

將已處理的發票資料匯出為報告格式。

## 前置準備

1. 確認已有處理過的發票資料（`data/receipts.csv` 存在）

## 匯出 Excel

// turbo
1. 執行匯出：
```bash
make export-excel
```

2. 查看產生的檔案：
```bash
ls -la exports/
```

## 匯出 PDF

// turbo
1. 執行匯出：
```bash
make export-pdf
```

## 輸出位置

所有匯出檔案儲存在 `exports/` 目錄：
- `trip_report_YYYYMMDD.xlsx`：Excel 報告
- `trip_report_YYYYMMDD.pdf`：PDF 報告

## 報告內容

- 消費摘要
- 每日消費明細
- 類別統計
- 店家列表
