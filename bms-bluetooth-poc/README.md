# BMS 藍牙通訊專案

🔋 成功實現與 DALY BMS (DL-411812013771) 的 D2 Modbus 藍牙通訊

## 🎯 專案狀態

✅ **協議破解完成** - D2 Modbus 協議成功實現  
✅ **數據驗證通過** - 電壓讀取準確度 ±0.1V  
✅ **BMS喚醒機制** - 自動化喚醒工具有效  

## 📁 專案結構

```
bms-bluetooth-poc/
├── core/                        # 🔧 核心功能
│   ├── daly_d2_modbus_test.py   # 主要協議實現
│   ├── bms_wake_tester.py       # BMS喚醒工具  
│   ├── config.py               # 配置檔案
│   └── requirements.txt        # Python依賴
├── tools/                       # 🛠️ 實用工具
│   └── scanner.py              # 藍牙掃描器
├── docs/                        # 📚 文檔
│   ├── PROJECT_STATUS.md       # 專案狀態
│   └── PROTOCOL_SUCCESS.md     # 協議成功記錄
├── data/                        # 📊 資料檔案
│   └── scan_results.txt        # 掃描結果
└── archive/                     # 📦 歷史檔案
    ├── research/               # 協議研究過程
    └── experiments/            # 實驗性工具
```

## 🚀 快速開始

### 1. 環境設定
```bash
# 啟動虛擬環境
source ../venv/bin/activate

# 確認依賴已安裝
pip install bleak
```

### 2. 執行測試
```bash
# 喚醒BMS (如果連接失敗)
python3 core/bms_wake_tester.py

# 執行完整協議測試
python3 core/daly_d2_modbus_test.py
```

### 3. 預期結果
- 總電壓: ~26.5V ✅
- 電芯電壓: 8串, 3.32V左右 ✅  
- 溫度: 4個感測器正常 ✅
- CRC驗證: 全部通過 ✅

## 📊 已驗證數據

| 項目 | Smart BMS App | D2 協議讀取 | 狀態 |
|------|---------------|-------------|------|
| 總電壓 | 26.6V | 26.5V | ✅ 極佳 |
| 電芯數 | 8串 | 8串 | ✅ 正確 |
| 電芯電壓 | 正常範圍 | 3.32~3.325V | ✅ 健康 |

## 🔧 技術細節

- **協議**: D2 Modbus RTU (CRC-16)
- **設備地址**: 0xD2  
- **BLE特徵**: fff2(寫) → fff1(讀)
- **關鍵寄存器**: 0x0028(總電壓), 0x0000+(電芯電壓)

## 📋 後續計劃

- [ ] 電流讀取校正
- [ ] SOC數據驗證  
- [ ] 即時監控界面
- [ ] 歷史數據記錄

詳細資訊請參閱 `docs/` 資料夾中的文檔。