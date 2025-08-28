"""
BMS 藍牙 POC 配置檔
根據你的 BMS 通訊協議文件設定
"""

# CAN 協議設定
CAN_BAUDRATE = 250000  # 250Kbps
CAN_ID_BMS_TO_CHARGER = 0x1806E5F4  # 報文1: BMS → 充電機
CAN_ID_CHARGER_BROADCAST = 0x18FF50E5  # 報文2: 充電機 → 廣播

# 數據格式設定
VOLTAGE_SCALE = 0.1  # 電壓縮放因子 (0.1V/bit)
CURRENT_SCALE = 0.1  # 電流縮放因子 (0.1A/bit)
SOC_SCALE = 0.1      # SOC 縮放因子 (0.1%/bit)

# 藍牙設定
BLUETOOTH_SCAN_TIMEOUT = 10  # 掃描超時時間 (秒)
BLUETOOTH_CONNECT_RETRY = 3  # 連線重試次數
DATA_RECEIVE_INTERVAL = 1    # 預期數據接收間隔 (秒)

# BMS 設備名稱特徵 (用於識別你的 BMS)
BMS_NAME_PATTERNS = [
    "DL-",
]

# 狀態位定義 (根據你的協議)
STATUS_FLAGS = {
    0: "硬件故障",
    1: "充電機溫度過高",
    2: "輸入電壓錯誤",
    3: "啟動狀態",
    4: "通信超時",
    5: "電池組異常",
}

# 告警閾值 (可根據需要調整)
VOLTAGE_WARNING_LOW = 45.0   # 低電壓警告 (V)
VOLTAGE_CRITICAL_LOW = 40.0  # 低電壓危險 (V)
VOLTAGE_WARNING_HIGH = 58.0  # 高電壓警告 (V)
CURRENT_WARNING_HIGH = 100.0 # 高電流警告 (A)
TEMP_WARNING_HIGH = 45.0     # 高溫警告 (°C)
TEMP_CRITICAL_HIGH = 55.0    # 高溫危險 (°C)
SOC_WARNING_LOW = 20.0        # 低 SOC 警告 (%)
SOC_CRITICAL_LOW = 10.0       # 低 SOC 危險 (%)

# 日誌設定
LOG_RAW_DATA = True          # 是否記錄原始數據
LOG_FILE = "bms_data.log"    # 日誌檔案名稱