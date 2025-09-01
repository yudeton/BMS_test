# 🪟 Windows 系統開發環境設置指南

> BMS 手機監控應用程式 Windows 開發環境完整設置教程

## 🎯 概述

本指南將協助您在 Windows 系統上設置完整的 React Native 開發環境，以便順利開發和測試 BMS 手機監控應用程式。

## 📋 系統需求

- **作業系統**: Windows 10/11 (64-bit)
- **記憶體**: 至少 8GB RAM (推薦 16GB)
- **硬碟空間**: 至少 20GB 可用空間
- **網路**: 穩定的網路連接（用於下載依賴）

## 🔧 環境安裝步驟

### 1. 安裝 Node.js

1. 前往 [Node.js 官網](https://nodejs.org/)
2. 下載 LTS 版本 (18.x 或更高)
3. 執行安裝程式，勾選 "Add to PATH" 選項
4. 驗證安裝：
   ```cmd
   node --version
   npm --version
   ```

### 2. 安裝 Java Development Kit (JDK)

1. 下載 [OpenJDK 17](https://adoptium.net/)
2. 安裝並設置環境變數：
   - `JAVA_HOME`: `C:\Program Files\Eclipse Adoptium\jdk-17.0.x-hotspot`
   - 將 `%JAVA_HOME%\bin` 加入 PATH

3. 驗證安裝：
   ```cmd
   java --version
   javac --version
   ```

### 3. 安裝 Android Studio

1. 下載 [Android Studio](https://developer.android.com/studio)
2. 安裝時選擇 "Custom" 安裝類型
3. 確保勾選以下組件：
   - Android SDK
   - Android SDK Platform
   - Android Virtual Device
   - Performance (Intel ® HAXM)

### 4. 設置 Android SDK

1. 開啟 Android Studio
2. 前往 **File → Settings → System Settings → Android SDK**
3. 在 **SDK Platforms** 標籤中，安裝：
   - Android 13.0 (API Level 33)
   - Android 12.0 (API Level 31)
   - Android 11.0 (API Level 30)

4. 在 **SDK Tools** 標籤中，確保已安裝：
   - Android SDK Build-Tools
   - Android Emulator
   - Android SDK Platform-Tools
   - Intel x86 Emulator Accelerator (HAXM installer)

### 5. 設置環境變數

在 Windows 環境變數中設置：

```
變數名: ANDROID_HOME
變數值: C:\Users\YourUsername\AppData\Local\Android\Sdk

在 PATH 中加入:
%ANDROID_HOME%\platform-tools
%ANDROID_HOME%\emulator
%ANDROID_HOME%\tools
%ANDROID_HOME%\tools\bin
```

### 6. 安裝 React Native CLI

```cmd
npm install -g react-native-cli
```

### 7. 驗證安裝

執行 React Native 環境檢查：
```cmd
npx react-native doctor
```

## 📱 創建和設置 Android 虛擬設備 (AVD)

### 1. 開啟 AVD Manager

在 Android Studio 中：
- 點擊 **Tools → AVD Manager**
- 或在歡迎畫面點擊 **Configure → AVD Manager**

### 2. 創建新的虛擬設備

1. 點擊 **Create Virtual Device**
2. 選擇設備型號（推薦 Pixel 4）
3. 選擇系統映像：
   - **推薦**: API 33, Android 13.0
   - 選擇 x86_64 架構（較快）
4. 設定 AVD 詳細資訊：
   - **AVD Name**: BMS_Test_Device
   - **Graphics**: Hardware - GLES 2.0
   - **Memory**: RAM 2048MB, Heap 512MB
5. 點擊 **Finish** 完成創建

### 3. 啟動虛擬設備

1. 在 AVD Manager 中找到創建的設備
2. 點擊 **Play** 按鈕啟動
3. 等待設備完全啟動（看到 Android 桌面）

## 🚀 專案設置和運行

### 1. 複製專案到 Windows

將專案資料夾複製到 Windows 系統，例如：
```
C:\Users\YourUsername\Projects\bms-mobile-app
```

### 2. 安裝專案依賴

在專案根目錄執行：
```cmd
cd C:\Users\YourUsername\Projects\bms-mobile-app
npm install
```

### 3. 啟動開發服務器

```cmd
# 啟動 Metro bundler（保持此終端開啟）
npm start
```

### 4. 運行應用程式

在新的命令提示字元視窗中：
```cmd
cd C:\Users\YourUsername\Projects\bms-mobile-app
npm run android
```

## 🔍 故障排除

### 常見問題與解決方案

#### 1. 模擬器無法啟動

**錯誤**: "Intel HAXM is required to run this AVD"
```cmd
# 解決方案：安裝 HAXM
# 前往 Android SDK 目錄執行：
C:\Users\YourUsername\AppData\Local\Android\Sdk\extras\intel\Hardware_Accelerated_Execution_Manager\intelhaxm-android.exe
```

#### 2. ADB 無法識別設備

**錯誤**: "No devices found"
```cmd
# 重啟 ADB 服務
adb kill-server
adb start-server
adb devices
```

#### 3. Metro 服務器端口衝突

**錯誤**: "Port 8081 already in use"
```cmd
# 使用不同端口啟動
npm start -- --port 8082
```

#### 4. Gradle 同步失敗

**錯誤**: "Could not resolve all dependencies"
```cmd
# 清理並重建
cd android
./gradlew clean
cd ..
npm run android
```

#### 5. 應用安裝失敗

**錯誤**: "Installation failed with message Failed to establish session"
```cmd
# 卸載舊版本
adb uninstall com.bmsmobileapp
npm run android
```

## 📱 實體設備測試

### Android 設備設置

1. **開啟開發者模式**：
   - 前往 **設定 → 關於手機**
   - 點擊 **版本號碼** 7次

2. **啟用 USB 偵錯**：
   - 前往 **設定 → 開發者選項**
   - 開啟 **USB 偵錯**

3. **連接設備**：
   - 使用 USB 線連接手機到電腦
   - 在手機上允許 USB 偵錯授權

4. **驗證連接**：
   ```cmd
   adb devices
   ```

5. **運行應用**：
   ```cmd
   npm run android
   ```

## 🛠️ 開發工具推薦

### 代碼編輯器
- **Visual Studio Code** (推薦)
  - React Native Tools 擴展
  - ES7+ React/Redux/React-Native snippets
  - TypeScript Hero

### 調試工具
- **Flipper**: React Native 官方調試工具
- **React Native Debugger**: 專用調試器
- **Android Studio Logcat**: 查看日誌

## 📊 效能優化建議

### 系統優化
1. 確保至少 16GB RAM
2. 使用 SSD 硬碟
3. 關閉不必要的背景程式
4. 設置 Windows 高效能模式

### 模擬器優化
1. 為模擬器分配充足記憶體
2. 啟用硬體加速
3. 使用較新的 API 級別
4. 避免同時運行多個模擬器

## 🔧 進階配置

### Gradle 配置優化

在 `android/gradle.properties` 中加入：
```properties
# 提高 Gradle 構建效能
org.gradle.daemon=true
org.gradle.parallel=true
org.gradle.jvmargs=-Xmx8192m -XX:MaxPermSize=512m -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8
```

### Metro 配置優化

在 `metro.config.js` 中：
```javascript
module.exports = {
  transformer: {
    getTransformOptions: async () => ({
      transform: {
        experimentalImportSupport: false,
        inlineRequires: true, // 啟用內聯 require
      },
    }),
  },
};
```

## ✅ 檢查清單

安裝完成後，確認以下項目：

- [ ] Node.js 18+ 已安裝
- [ ] Java JDK 17 已安裝並設置環境變數
- [ ] Android Studio 已安裝
- [ ] Android SDK 已安裝並設置 ANDROID_HOME
- [ ] React Native CLI 已全域安裝
- [ ] AVD 已創建並可正常啟動
- [ ] adb devices 可以識別模擬器或實體設備
- [ ] npm run android 可以成功運行
- [ ] 應用程式可以在設備上正常顯示

## 📞 技術支援

如果在設置過程中遇到問題：

1. **檢查 React Native 環境**：
   ```cmd
   npx react-native doctor
   ```

2. **查看詳細錯誤日誌**：
   ```cmd
   npx react-native run-android --verbose
   ```

3. **重置 Metro 快取**：
   ```cmd
   npm start -- --reset-cache
   ```

---

**🎉 設置完成後，您就可以在 Windows 系統上順利開發和測試 BMS 監控應用程式了！**