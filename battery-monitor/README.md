# 電池監控系統 (Battery Monitor)

即時電池監控與管理系統，支援 PWA 跨平台訪問、歷史數據記錄與告警功能。

## 系統特色

- **即時監控**: WebSocket 連線，實時顯示電池總壓、電流、功率、SOC 狀態
- **細節監控**: 顯示每串 cell 電壓，支援異常檢測
- **歷史數據**: 3分鐘彙整存檔，提供 1h/24h/7d/30d 圖表瀏覽  
- **PWA 支援**: 手機、電腦開啟網頁即可使用，支援離線緩存
- **區網優先**: 內網獨立運作，可擴展至雲端
- **高可靠性**: 自動重連、本地快取、數據補傳

## 技術架構

### 後端
- **Node.js + Express**: HTTP API 服務
- **WebSocket**: 即時數據推送
- **MQTT**: 設備通訊協議
- **SQLite**: 本地資料庫
- **Redis**: 即時數據快取

### 前端
- **React 18 + Vite**: 現代化前端框架
- **PWA**: 支援離線使用與推播通知
- **Chart.js**: 圖表展示
- **Tailwind CSS**: UI 設計
- **React Hot Toast**: 通知系統

## 快速開始

### 使用 Docker Compose (推薦)

```bash
# 啟動所有服務
docker-compose up -d

# 查看日誌
docker-compose logs -f

# 停止服務
docker-compose down
```

服務將在以下端口啟動：
- 前端: http://localhost:80
- 後端 API: http://localhost:3001
- WebSocket: ws://localhost:3002
- MQTT: tcp://localhost:1883
- Redis: localhost:6379

### 手動開發模式

#### 後端服務

```bash
cd backend
npm install
npm run dev
```

#### 前端服務

```bash  
cd frontend
npm install
npm run dev
```

## MQTT 數據格式

系統通過 MQTT 接收電池數據，支援以下 topic：

### battery/realtime
```json
{
  "voltage": 48.5,
  "current": -12.3,
  "power": 596.55,
  "soc": 85.2,
  "temperature": 28.5,
  "status": "normal",
  "cells": [3.85, 3.84, 3.86, 3.83, ...]
}
```

### battery/alerts
```json
{
  "type": "low_voltage",
  "severity": "warning",
  "message": "Battery voltage low: 45.2V",
  "value": 45.2
}
```

## API 端點

### 即時數據
- `GET /api/realtime` - 獲取最新數據
- `GET /api/cells` - 獲取電池串數據
- `GET /api/alerts` - 獲取告警列表

### 歷史數據  
- `GET /api/history/:duration` - 歷史數據 (1h/24h/7d/30d)
- `GET /api/aggregated/:interval` - 聚合數據 (3min/1hour/1day)

### 系統狀態
- `GET /api/stats` - 系統統計信息
- `POST /api/alerts/:id/acknowledge` - 確認告警

## 系統配置

### 環境變數 (.env)

```bash
# 伺服器配置
PORT=3001
WS_PORT=3002

# MQTT 設定
MQTT_BROKER_URL=mqtt://localhost:1883
MQTT_TOPIC_PREFIX=battery/

# 資料庫
DB_PATH=./data/battery.db

# Redis 快取
REDIS_HOST=localhost
REDIS_PORT=6379

# 數據採集
SAMPLING_INTERVAL_MS=180000
DATA_RETENTION_DAYS=30
```

## 告警閾值

系統內建以下告警規則：

- **低電壓**: < 40V (critical), < 45V (warning)
- **高電壓**: > 58V (warning)  
- **大電流**: > 100A (warning)
- **高溫**: > 55°C (critical), > 45°C (warning)
- **低 SOC**: < 10% (critical), < 20% (warning)

## PWA 功能

- ✅ 離線緩存
- ✅ 桌面安裝
- ✅ 推播通知 (計劃中)
- ✅ 背景同步

## 開發計畫

### Phase 1 (已完成)
- [x] 基礎架構與 MQTT 接收
- [x] 即時數據 WebSocket 推送
- [x] React PWA 前端
- [x] Docker 容器化部署

### Phase 2 (進行中)
- [ ] 用戶認證與權限管理
- [ ] HTTPS/TLS 加密
- [ ] 推播通知功能
- [ ] 數據導出功能

### Phase 3 (計劃中)  
- [ ] 雲端橋接功能
- [ ] 多設備管理
- [ ] 報表生成
- [ ] 移動端 App

## 故障排除

### 常見問題

**Q: 前端無法連接到後端**
A: 檢查 API 代理設置，確保後端服務運行在正確端口

**Q: WebSocket 連接失敗**  
A: 確認防火牆設置，WebSocket 需要 3002 端口

**Q: MQTT 數據沒有接收到**
A: 檢查 MQTT broker 連接狀態和 topic 設置

**Q: 歷史數據圖表不顯示**
A: 確認資料庫中有數據，檢查聚合任務是否正常運行

## 貢獻指南

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)  
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 建立 Pull Request

## 授權

本專案採用 MIT 授權 - 詳見 [LICENSE](LICENSE) 檔案

## 聯繫方式

專案連結: [https://github.com/yourusername/battery-monitor](https://github.com/yourusername/battery-monitor)