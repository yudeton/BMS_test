#!/bin/bash

# BMS Mobile App 專案設置腳本

echo "🚀 設置 BMS 手機監控應用程式..."

# 檢查 Node.js 版本
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安裝，請先安裝 Node.js 16 或更高版本"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    echo "❌ Node.js 版本過低，需要 16 或更高版本"
    exit 1
fi

echo "✅ Node.js 版本: $(node -v)"

# 檢查 React Native CLI
if ! command -v react-native &> /dev/null; then
    echo "⚠️  React Native CLI 未安裝，正在安裝..."
    npm install -g react-native-cli
fi

# 安裝依賴
echo "📦 安裝專案依賴..."
npm install

# 檢查平台特定設置
echo "🔍 檢查平台設置..."

# iOS 設置（如果是 macOS）
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 檢測到 macOS，設置 iOS 依賴..."
    
    # 檢查 CocoaPods
    if ! command -v pod &> /dev/null; then
        echo "⚠️  CocoaPods 未安裝，正在安裝..."
        sudo gem install cocoapods
    fi
    
    # 安裝 iOS 依賴
    cd ios && pod install && cd ..
    echo "✅ iOS 依賴安裝完成"
else
    echo "ℹ️  非 macOS 系統，跳過 iOS 設置"
fi

# Android 設置檢查
if [ -d "$HOME/Android/Sdk" ] || [ -n "$ANDROID_HOME" ]; then
    echo "✅ Android SDK 已設置"
else
    echo "⚠️  Android SDK 未找到，請確保已安裝 Android Studio"
fi

# 創建必要的目錄
echo "📁 創建必要目錄..."
mkdir -p android/app/src/main/res/drawable
mkdir -p ios/BMSMobileApp/Images.xcassets

# 設置權限（Android）
echo "📱 設置 Android 權限..."
cat > android/app/src/main/AndroidManifest.xml << 'EOF'
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.bmsmobileapp">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.BLUETOOTH" />
    <uses-permission android:name="android.permission.BLUETOOTH_ADMIN" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.VIBRATE" />
    
    <!-- Android 12+ 藍牙權限 -->
    <uses-permission android:name="android.permission.BLUETOOTH_SCAN" />
    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
    <uses-permission android:name="android.permission.BLUETOOTH_ADVERTISE" />

    <application
        android:name=".MainApplication"
        android:label="@string/app_name"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:allowBackup="false"
        android:theme="@style/AppTheme">
        
        <activity
            android:name=".MainActivity"
            android:label="@string/app_name"
            android:configChanges="keyboard|keyboardHidden|orientation|screenSize|uiMode"
            android:launchMode="singleTask"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
EOF

echo "✅ 專案設置完成！"
echo ""
echo "🎯 下一步："
echo "1. 啟動 Metro bundler: npm start"
echo "2. 運行 Android 版本: npm run android"
echo "3. 運行 iOS 版本: npm run ios (僅限 macOS)"
echo ""
echo "📋 注意事項："
echo "• 確保藍牙設備已開啟"
echo "• Android 需要位置權限才能掃描藍牙設備"
echo "• 首次運行可能需要較長時間編譯"
echo ""
echo "🔧 如果遇到問題："
echo "• 清理快取: npm start --reset-cache"
echo "• 重建專案: npm run clean && npm install"
echo "• 查看日誌: npx react-native log-android 或 npx react-native log-ios"