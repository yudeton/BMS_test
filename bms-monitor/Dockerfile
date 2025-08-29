# 使用 Python 3.11 作為基礎映像
FROM python:3.11-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴 (藍牙和 D-Bus 支援)
RUN apt-get update && apt-get install -y \
    bluetooth \
    bluez \
    bluez-tools \
    dbus \
    libdbus-1-dev \
    pkg-config \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 複製需求檔案 (從 docker-compose build context 複製)
COPY requirements.txt ./requirements.txt

# 安裝 Python 依賴
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY ./bms-monitor/app ./app

# 複製藍牙初始化腳本
COPY ./bms-monitor/bluetooth-init.sh /usr/local/bin/bluetooth-init.sh
RUN chmod +x /usr/local/bin/bluetooth-init.sh

# 創建非 root 使用者 (但保持必要權限)
RUN groupadd -r appuser && \
    useradd -r -g appuser appuser && \
    usermod -a -G bluetooth appuser && \
    chown -R appuser:appuser /app

# 暴露端口
EXPOSE 8000 8001

# 設置環境變數
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/docs || exit 1

# 保持 root 用戶以訪問藍牙
# USER appuser

# 啟動命令 (使用模組模式執行)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]