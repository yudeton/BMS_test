# 🔋 DALY BMS 監控系統

**基於 FastAPI 的專業級電池管理系統 Web 監控解決方案**

## 📊 系統概述

本系統成功破解了 DALY BMS D2 Modbus 藍牙通訊協議，並建立了完整的 Web 監控界面，提供即時電池數據監控、歷史數據分析和智能警報功能。

### ✅ 已驗證功能
- **精準數據讀取**: 總電壓 26.5V (±0.1V)，8串電芯電壓監控
- **即時通訊**: 30秒數據更新，WebSocket 即時推送
- **完整 API**: RESTful API + 自動文檔生成
- **高效快取**: Redis 緩存提升響應速度
- **跨平台**: 手機 PWA + 電腦 Web 界面

## 🏗️ 專案架構

```
battery/
├── bms-monitor/              # 主要 FastAPI 監控系統
│   ├── app/
│   │   ├── api/             # REST API 端點
│   │   ├── models/          # 數據模型
│   │   ├── services/        # 核心服務
│   │   └── utils/           # BMS 通訊工具
│   ├── venv/                # Python 虛擬環境
│   └── requirements.txt     # 依賴管理
├── bms-bluetooth-poc/       # BMS 通訊協議研究
│   └── core/               # 核心通訊模組
└── docs/                   # 技術文檔
```

## 🚀 快速啟動

### 1. 啟動監控系統
```bash
cd bms-monitor
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 存取界面
- **Web 界面**: http://localhost:8000
- **API 文檔**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:8000/ws

### 3. BMS 測試 (可選)
```bash
cd bms-bluetooth-poc
python3 core/bms_wake_tester.py
python3 core/daly_d2_modbus_test.py
```

## 🔧 技術細節

### 協議突破
- **協議類型**: D2 Modbus RTU (8字節 + CRC-16)
- **設備地址**: 0xD2
- **BLE 特徵**: fff2(寫入) → fff1(讀取)
- **關鍵發現**: 電流使用 30000 偏移編碼

### 寄存器映射
```python
registers = {
    "total_voltage": 0x0028,      # 總電壓 (0.1V/bit)
    "current": 0x0029,            # 電流 (偏移編碼)
    "cell_voltage_base": 0x0000,  # 電芯電壓起始
    "temperature_base": 0x0020,   # 溫度起始
}
```

### 核心技術棧
- **後端**: FastAPI + Python 3.8+
- **資料庫**: SQLite + SQLAlchemy ORM
- **緩存**: Redis
- **通訊**: WebSocket + MQTT
- **BMS 協議**: DALY D2 Modbus over Bluetooth

## 📊 驗證結果

| 項目 | Smart BMS App | 本專案讀取 | 狀態 |
|------|---------------|------------|------|
| 總電壓 | 26.6V | 26.5V | ✅ 極佳 (-0.1V) |
| 電芯數量 | 8串 | 8串 | ✅ 完全正確 |
| 電芯電壓 | 正常範圍 | 3.32~3.325V | ✅ 健康狀態 |
| 電流狀態 | 靜止 | 0.0A | ✅ 準確 |
| 溫度感測 | 4個點 | 4個感測器 | ✅ 正常 |

## 🛠️ 開發歷程亮點

### 協議研究過程
1. **多協議嘗試** - 測試了 Smart BMS (DD A5)、標準 DALY (A5) 等協議
2. **AI 輔助探索** - 使用遺傳演算法發現有效命令模式
3. **網路協作研究** - 發現 K00T 韌體使用非標準 D2 Modbus
4. **數據分析突破** - 成功解析電流偏移編碼

### 關鍵技術突破
- **BMS 喚醒機制** - 解決休眠狀態連線問題
- **CRC-16 驗證** - 標準 Modbus 校驗完全通過
- **偏移編碼解析** - 發現 30000 為電流零點
- **多溫度點讀取** - 成功讀取 4個溫度感測器

## 📚 詳細文檔

- **[協議成功記錄](bms-bluetooth-poc/docs/PROTOCOL_SUCCESS.md)** - 詳細的技術突破記錄
- **[專案狀態](bms-bluetooth-poc/docs/PROJECT_STATUS.md)** - 完整的開發歷程
- **[Web 監控說明](battery-monitor/README.md)** - 監控系統使用指南

## 🔬 研究價值

### 學術貢獻
- **協議逆向工程** - DALY BMS K00T 韌體協議完整破解
- **AI 輔助方法** - 遺傳演算法在協議探索中的應用
- **偏移編碼分析** - 電流測量中偏移編碼的發現與解析

### 實用價值  
- **開源 BMS 監控** - 完整的電池監控解決方案
- **成本節省** - 無需購買昂貴的商業監控系統
- **客製化彈性** - 可根據需求調整功能

## 🎯 未來發展

### 短期目標
- [ ] SOC (電量百分比) 數據驗證
- [ ] MOSFET 狀態監控
- [ ] 故障代碼解析
- [ ] 手機 App 開發

### 長期願景
- [ ] 支援多種 BMS 品牌
- [ ] 雲端數據同步
- [ ] 機器學習電池健康預測
- [ ] 商業化部署方案

## 🤝 貢獻

歡迎各種形式的貢獻：
- 🐛 問題回報
- 💡 功能建議  
- 🔧 程式碼改進
- 📖 文檔完善

## 📜 授權

本專案採用 MIT 授權條款，詳見 [LICENSE](LICENSE) 檔案。

## 🙏 致謝

- **DALY BMS** 提供了優秀的硬體平台
- **Claude Code** 在協議研究中提供了重要協助
- **開源社群** 提供了豐富的技術資源

---

**⭐ 如果這個專案對您有幫助，請給個星星支持！**

**📧 聯絡**: 如有技術問題或合作意向，歡迎 Issue 或 PR

---
*最後更新：2025-08-28*  
*專案狀態：🎉 協議破解與系統實現完全成功*
