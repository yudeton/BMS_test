# ===========================================
# 🔋 DALY BMS 監控系統 - Makefile
# ===========================================

.PHONY: help dev docker-up docker-down docker-build docker-logs test lint format clean install

# 預設目標
help: ## 顯示可用的命令
	@echo "🔋 DALY BMS 監控系統 - 可用命令:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# 開發環境
dev: ## 啟動開發環境 (本機 FastAPI)
	@echo "🚀 啟動開發環境..."
	@if [ ! -d "venv" ]; then python3 -m venv venv; fi
	@venv/bin/pip install --upgrade pip
	@venv/bin/pip install -r requirements.txt
	@echo "✅ 依賴已安裝，啟動 FastAPI 開發伺服器..."
	@cd bms-monitor && ../venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

install: ## 安裝或更新依賴
	@echo "📦 安裝依賴..."
	@if [ ! -d "venv" ]; then python3 -m venv venv; fi
	@venv/bin/pip install --upgrade pip
	@venv/bin/pip install -r requirements.txt
	@echo "✅ 依賴安裝完成"

# Docker 管理
docker-up: ## 啟動 Docker 服務
	@echo "🐳 啟動 Docker 服務..."
	@docker compose up -d
	@echo "✅ Docker 服務已啟動"
	@echo "📊 API 文檔: http://localhost:8000/docs"
	@echo "🔍 容器狀態: make docker-logs"

docker-down: ## 停止 Docker 服務
	@echo "🛑 停止 Docker 服務..."
	@docker compose down
	@echo "✅ Docker 服務已停止"

docker-build: ## 重新構建並啟動 Docker 服務
	@echo "🔨 重新構建 Docker 映像..."
	@docker compose up --build -d
	@echo "✅ Docker 服務重建完成"

docker-logs: ## 查看 Docker 日誌
	@echo "📋 Docker 服務日誌:"
	@docker compose logs -f --tail=50

# 開發工具
test: ## 執行測試 (待實作)
	@echo "🧪 執行測試..."
	@echo "⚠️  測試框架尚未實作，將在後續階段加入"
	# @venv/bin/python -m pytest tests/ -v

lint: ## 程式碼檢查 (待實作)
	@echo "🔍 程式碼檢查..."
	@echo "⚠️  代碼檢查工具尚未配置，將在後續階段加入"
	# @venv/bin/python -m ruff check .
	# @venv/bin/python -m mypy bms-monitor/

format: ## 程式碼格式化 (待實作)
	@echo "✨ 程式碼格式化..."
	@echo "⚠️  代碼格式化工具尚未配置，將在後續階段加入"
	# @venv/bin/python -m black .
	# @venv/bin/python -m isort .

# 清理
clean: ## 清理臨時檔案
	@echo "🧹 清理臨時檔案..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ 清理完成"

# 狀態檢查
status: ## 檢查系統狀態
	@echo "🔋 BMS 監控系統狀態:"
	@echo ""
	@echo "📦 Docker 容器:"
	@docker ps --filter "name=battery-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  無 Docker 容器運行"
	@echo ""
	@echo "🌐 服務端點:"
	@echo "  • API 文檔: http://localhost:8000/docs"
	@echo "  • API 狀態: http://localhost:8000/api/status"
	@echo "  • PostgreSQL: localhost:5432"
	@echo "  • Redis: localhost:6379"
	@echo "  • MQTT: localhost:1884"
	@echo ""

# 快速啟動指南
quickstart: ## 快速啟動指南
	@echo "🚀 DALY BMS 監控系統 - 快速啟動:"
	@echo ""
	@echo "1. 開發模式 (本機):"
	@echo "   make dev"
	@echo ""
	@echo "2. 生產模式 (Docker):"
	@echo "   make docker-up"
	@echo ""
	@echo "3. 檢查狀態:"
	@echo "   make status"
	@echo ""
	@echo "4. 查看日誌:"
	@echo "   make docker-logs"
	@echo ""
	@echo "更多命令請執行: make help"