# 🔋 BMS 手機監控應用程式

> 專業級電池管理系統 (Battery Management System) 手機監控應用程式  
> 支援 DALY BMS D2 Modbus 協議，完全離線運行，無雲端依賴

基於 React Native + TypeScript 開發的專業級 BMS 監控應用程式，專為監控 LiFePO4 電池組而設計。應用程式採用完全離線架構，直接透過藍牙連接 DALY BMS，提供即時監控、智能警報和數據分析功能。

## 📊 專案狀態

✅ **核心架構已完成** - 嚴格分層架構、依賴注入、服務層實作完成  
✅ **BMS 通訊** - DALY D2 Modbus 協議移植完成，支援藍牙直連  
✅ **數據持久化** - AsyncStorage + SQLite 分層存儲實作完成  
✅ **本地通知** - Notifee 離線通知系統實作完成  
🚧 **UI 層開發中** - 基礎組件和儀表板界面待完成  

## 🏗️ 架構設計

### 嚴格分層架構
```
src/
├── services/           # 服務層（純邏輯）
│   ├── interfaces/     # 服務介面定義
│   ├── implementations/ # 具體實作
│   └── ServiceContainer.ts # 依賴注入容器
├── domain/             # 領域層
│   ├── entities/       # 實體模型
│   └── usecases/       # 用例（業務邏輯）
├── presentation/       # 展示層
│   ├── viewmodels/     # MVVM 架構
│   ├── screens/        # 頁面組件
│   └── components/     # UI 組件
└── utils/              # 工具函數
```

### 核心技術棧
- **框架**: React Native + TypeScript
- **架構模式**: Clean Architecture + MVVM
- **依賴注入**: TSyringe
- **藍牙通訊**: react-native-ble-plx
- **本地通知**: @notifee/react-native
- **數據存儲**: 
  - **輕量配置**: AsyncStorage
  - **結構化數據**: SQLite
- **狀態管理**: MobX

## 🔧 已實作功能

### 1. BLE 藍牙服務 (`BLEService`)
- ✅ 完整的 DALY BMS D2 Modbus 協議實作
- ✅ 自動重連和錯誤恢復機制
- ✅ 設備掃描和連接管理
- ✅ 數據讀取和解析
- ✅ 連接狀態監控

### 2. 本地通知服務 (`NotificationService`) 
- ✅ Notifee 集成，完全離線運作
- ✅ 分級通知通道（危險/警告/資訊）
- ✅ 背景通知處理
- ✅ 通知動作支援（確認/稍後提醒）
- ✅ 跨平台兼容（iOS/Android）

### 3. 分層數據持久化 (`StorageService`)
- ✅ AsyncStorage 層：輕量配置存儲
- ✅ SQLite 層：結構化數據存儲
- ✅ 電池數據和警報記錄管理
- ✅ 數據匯出和清理功能
- ✅ 統計資訊查詢

### 4. 數據處理服務 (`DataService`)
- ✅ 數據驗證和轉換
- ✅ 警報規則引擎
- ✅ 電池健康評估
- ✅ 統計分析和異常檢測
- ✅ 數據平滑和預測

### 5. 業務用例層
- ✅ **電池監控用例** (`MonitorBatteryUseCase`)
  - 監控生命週期管理
  - 自動重連機制
  - 數據讀取和存儲協調
  - 統計和健康評估

- ✅ **警報處理用例** (`HandleAlertsUseCase`)
  - 即時警報檢查
  - 通知發送管理
  - 警報確認和解決
  - 冷卻期控制

### 6. ViewModel 層 (MVVM)
- ✅ **基礎 ViewModel** (`BaseViewModel`)
  - 通用狀態管理
  - 錯誤處理和重試機制
  - 異步操作包裝器

- ✅ **儀表板 ViewModel** (`DashboardViewModel`)
  - 即時數據綁定
  - 自動更新機制
  - 計算屬性（健康狀態、警報等級等）
  - 完整的監控控制邏輯

## 📱 核心特性

### 🔵 完全離線運作
- **零雲端依賴**: 所有功能本地運行
- **即時響應**: 無網路延遲
- **隱私保護**: 數據不離開設備
- **穩定可靠**: 不受網路狀況影響

### 🔵 專業級架構
- **依賴注入**: 100% 可測試的服務層
- **嚴格分層**: 邏輯與 UI 完全解耦
- **MVVM 模式**: 響應式數據綁定
- **錯誤處理**: 完整的異常恢復機制

### 🔵 進階功能
- **智能警報**: 多級警報規則引擎
- **健康評估**: 電池狀態分析
- **數據分析**: 趨勢預測和異常檢測
- **背景監控**: 應用在背景時持續運作

## 🔄 開發進度

### Phase 1: 核心架構 ✅ (已完成)
- [x] React Native 專案建立
- [x] 依賴注入框架設定
- [x] 服務層介面定義
- [x] BMS 協議移植
- [x] 分層存儲實作

### Phase 2: 業務邏輯 ✅ (已完成)  
- [x] BLE 通訊服務實作
- [x] 本地通知服務實作
- [x] 數據處理服務實作
- [x] Use Case 層實作
- [x] ViewModel 層實作

### Phase 3: UI 開發 🚧 (進行中)
- [ ] 基礎 UI 組件實作
- [ ] 主儀表板畫面
- [ ] 設定頁面
- [ ] 警報管理界面
- [ ] 歷史數據圖表

### Phase 4: 測試與優化 📋 (待開始)
- [ ] 單元測試覆蓋
- [ ] 整合測試
- [ ] UI/UX 優化
- [ ] 效能調優
- [ ] 發布準備

## 🚀 快速開始

### 環境要求
- Node.js >= 16
- React Native CLI
- Android Studio / Xcode
- 支援 Bluetooth LE 的設備

### 安裝依賴
```bash
cd bms-mobile-app
npm install

# iOS 額外步驟
cd ios && pod install
```

### 啟動開發服務器
```bash
# 啟動 Metro bundler
npm start

# 運行 Android 版本
npm run android

# 運行 iOS 版本 (需要 macOS)
npm run ios
```

## 📋 配置說明

### BMS 設備配置
預設配置支援 DALY BMS (8S LiFePO4)：
- MAC 地址：`41:18:12:01:37:71`
- 協議：D2 Modbus RTU
- 讀取間隔：30 秒
- 自動重連：啟用

### 警報規則
內建警報規則包括：
- 電壓異常 (< 24V 或 > 30.4V)
- 溫度過高 (> 45°C)
- 電量不足 (< 20%)
- 連接中斷

## 🧪 測試

### 運行測試
```bash
# 單元測試
npm test

# 類型檢查
npm run type-check

# 程式碼檢查
npm run lint
```

### 服務層測試
所有核心服務都設計為可完全測試：
- 依賴注入支援 Mock
- 介面抽象化
- 純函數設計

## 📖 技術文檔

### 服務介面
- `IBLEService`: 藍牙通訊介面
- `INotificationService`: 通知服務介面  
- `IStorageService`: 存儲服務介面
- `IDataService`: 數據處理介面

### 核心用例
- `MonitorBatteryUseCase`: 電池監控業務邏輯
- `HandleAlertsUseCase`: 警報處理業務邏輯

### ViewModel
- `BaseViewModel`: 基礎狀態管理
- `DashboardViewModel`: 儀表板狀態管理

## 🤝 開發指南

### 新增服務
1. 在 `interfaces/` 定義介面
2. 在 `implementations/` 實作服務
3. 在 `ServiceRegistry.ts` 註冊服務
4. 編寫單元測試

### 新增頁面
1. 創建 ViewModel 繼承 `BaseViewModel`
2. 實作頁面組件
3. 在導航中註冊路由

### 最佳實務
- 遵循 Clean Architecture 原則
- 使用依賴注入避免硬耦合
- 所有異步操作都要有錯誤處理
- UI 組件保持純展示功能

## 📄 授權

MIT License - 詳見 [LICENSE](../LICENSE) 檔案

## 🙏 致謝

感謝原始專案的電池通訊協議研究成果，為本手機應用的開發提供了堅實的技術基礎。

---

**📱 目標**: 打造專業、穩定、用戶友好的 BMS 手機監控應用  
**🎯 特色**: 完全離線、即時響應、智能警報、專業架構  
**⭐ 現況**: 核心架構完成，UI 開發中，預計 2 週內完成 MVP**