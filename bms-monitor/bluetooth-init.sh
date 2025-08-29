#!/bin/bash
# 藍牙初始化腳本

echo "初始化藍牙服務..."

# 啟動 D-Bus 服務
service dbus start

# 等待 D-Bus 就緒
sleep 2

# 啟動藍牙服務
service bluetooth start

# 等待藍牙服務就緒
sleep 3

# 檢查藍牙狀態
if bluetoothctl --timeout 5 list; then
    echo "✅ 藍牙初始化成功"
else
    echo "⚠️  藍牙初始化失敗，但繼續運行"
fi

# 啟動應用程式
exec "$@"
