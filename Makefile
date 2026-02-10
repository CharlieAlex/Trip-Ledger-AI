.PHONY: install sync run extract extract-force export clean-cache clean-all test lint

# 同步依賴
sync:
	uv sync

# 安裝開發依賴
install-dev:
	uv sync --all-extras

# 啟動應用
run:
	uv run streamlit run src/app.py

# 處理發票（使用快取）
extract:
	uv run python -m src.extractors.invoice_parser

# 強制重新處理（忽略快取）
extract-force:
	uv run python -m src.extractors.invoice_parser --force

# 匯出報告（FORMAT=excel 或 FORMAT=pdf）
export:
	uv run python -m src.etl.exporter --format=$(FORMAT)

# 匯出 Excel
export-excel:
	uv run python -m src.etl.exporter --format=excel

# 匯出 PDF
export-pdf:
	uv run python -m src.etl.exporter --format=pdf

# 清除快取
clean-cache:
	rm -rf data/cache/*

# 清除所有資料
clean-all:
	rm -rf data/cache/* data/*.csv exports/*

# 執行測試
test:
	uv run pytest tests/ -v

# 執行測試並產生覆蓋率報告
test-cov:
	uv run pytest tests/ -v --cov=src --cov-report=html

# 顯示幫助
help:
	@echo "Trip Ledger AI - 可用指令："
	@echo ""
	@echo "  make sync          - 同步依賴"
	@echo "  make run           - 啟動 Streamlit 應用"
	@echo "  make extract       - 處理發票照片（使用快取）"
	@echo "  make extract-force - 強制重新處理所有發票"
	@echo "  make export-excel  - 匯出 Excel 報告"
	@echo "  make export-pdf    - 匯出 PDF 報告"
	@echo "  make clean-cache   - 清除快取"
	@echo "  make clean-all     - 清除所有資料"
	@echo "  make test          - 執行測試"
	@echo "  make help          - 顯示此幫助"
