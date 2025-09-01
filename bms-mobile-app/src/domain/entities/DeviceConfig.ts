/**
 * BMS 設備類型枚舉
 */
export enum BMSDeviceType {
  DALY_BMS = 'daly_bms',
  JBD_BMS = 'jbd_bms',
  OTHER = 'other'
}

/**
 * 連接模式枚舉
 */
export enum ConnectionMode {
  BLUETOOTH = 'bluetooth',
  WIFI = 'wifi',
  SERIAL = 'serial'
}

/**
 * 設備配置實體
 * 儲存 BMS 設備的配置資訊
 */
export interface DeviceConfig {
  /** 配置 ID */
  id: string;

  /** 設備名稱（使用者自定義） */
  name: string;

  /** 設備類型 */
  deviceType: BMSDeviceType;

  /** 連接模式 */
  connectionMode: ConnectionMode;

  /** 藍牙 MAC 地址（藍牙連接時使用） */
  bluetoothAddress?: string;

  /** WiFi 設置（WiFi 連接時使用） */
  wifiConfig?: {
    ipAddress: string;
    port: number;
    username?: string;
    password?: string;
  };

  /** BMS 協議設定 */
  protocolConfig: {
    /** 設備地址 */
    deviceAddress: number;
    
    /** 讀取間隔（秒） */
    readInterval: number;
    
    /** 連接超時（秒） */
    connectionTimeout: number;
    
    /** 重試次數 */
    maxRetries: number;
    
    /** SOC 寄存器地址 */
    socRegister: number;
    
    /** SOC 縮放係數 */
    socScale: number;
    
    /** SOC 偏移量 */
    socOffset: number;
  };

  /** 電池規格 */
  batterySpecs: {
    /** 電芯串數 */
    cellCount: number;
    
    /** 標稱容量 (Ah) */
    nominalCapacity: number;
    
    /** 標稱電壓 (V) */
    nominalVoltage: number;
    
    /** 最大電壓 (V) */
    maxVoltage: number;
    
    /** 最小電壓 (V) */
    minVoltage: number;
    
    /** 最大充電電流 (A) */
    maxChargeCurrent: number;
    
    /** 最大放電電流 (A) */
    maxDischargeCurrent: number;
    
    /** 電池化學類型 */
    chemistry: 'LiFePO4' | 'Li-ion' | 'Lead-acid' | 'Other';
  };

  /** 監控設定 */
  monitoringConfig: {
    /** 是否啟用自動連接 */
    autoConnect: boolean;
    
    /** 是否啟用背景監控 */
    backgroundMonitoring: boolean;
    
    /** 數據保存天數 */
    dataRetentionDays: number;
    
    /** 是否啟用數據導出 */
    enableDataExport: boolean;
  };

  /** 通知設定 */
  notificationConfig: {
    /** 是否啟用通知 */
    enabled: boolean;
    
    /** 是否啟用聲音 */
    sound: boolean;
    
    /** 是否啟用震動 */
    vibration: boolean;
    
    /** 靜音時段 */
    quietHours?: {
      enabled: boolean;
      startTime: string; // HH:MM 格式
      endTime: string;   // HH:MM 格式
    };
  };

  /** 創建時間 */
  createdAt: string;

  /** 最後修改時間 */
  updatedAt: string;

  /** 最後連接時間 */
  lastConnectedAt?: string;

  /** 是否為預設配置 */
  isDefault: boolean;
}

/**
 * 應用程式設定實體
 * 儲存全域應用程式設定
 */
export interface AppConfig {
  /** 版本號 */
  version: string;

  /** 主題模式 */
  theme: 'light' | 'dark' | 'auto';

  /** 語言設定 */
  language: 'zh-TW' | 'zh-CN' | 'en' | 'ja';

  /** 單位設定 */
  units: {
    temperature: 'celsius' | 'fahrenheit';
    power: 'watts' | 'kilowatts';
    energy: 'wh' | 'kwh';
  };

  /** 介面設定 */
  ui: {
    /** 是否顯示進階資訊 */
    showAdvancedInfo: boolean;
    
    /** 圖表更新間隔（秒） */
    chartUpdateInterval: number;
    
    /** 是否啟用動畫 */
    enableAnimations: boolean;
    
    /** 是否保持螢幕常亮 */
    keepScreenOn: boolean;
  };

  /** 安全設定 */
  security: {
    /** 是否需要生物識別認證 */
    biometricAuth: boolean;
    
    /** 自動鎖定時間（分鐘） */
    autoLockMinutes: number;
    
    /** 是否允許截圖 */
    allowScreenshots: boolean;
  };

  /** 偵錯設定（開發用） */
  debug?: {
    /** 是否啟用偵錯模式 */
    enabled: boolean;
    
    /** 日誌等級 */
    logLevel: 'error' | 'warn' | 'info' | 'debug';
    
    /** 是否保存日誌到檔案 */
    saveLogsToFile: boolean;
    
    /** 是否顯示效能資訊 */
    showPerformanceInfo: boolean;
  };

  /** 最後修改時間 */
  updatedAt: string;
}

/**
 * 預設設備配置（8S LiFePO4）
 */
export const DEFAULT_DEVICE_CONFIG: Omit<DeviceConfig, 'id' | 'createdAt' | 'updatedAt'> = {
  name: 'DALY BMS',
  deviceType: BMSDeviceType.DALY_BMS,
  connectionMode: ConnectionMode.BLUETOOTH,
  bluetoothAddress: '41:18:12:01:37:71',
  
  protocolConfig: {
    deviceAddress: 0xD2,
    readInterval: 30,
    connectionTimeout: 10,
    maxRetries: 3,
    socRegister: 0x002C,
    socScale: 0.1,
    socOffset: 0.0
  },

  batterySpecs: {
    cellCount: 8,
    nominalCapacity: 100,
    nominalVoltage: 25.6,
    maxVoltage: 29.2,
    minVoltage: 24.0,
    maxChargeCurrent: 100,
    maxDischargeCurrent: 100,
    chemistry: 'LiFePO4'
  },

  monitoringConfig: {
    autoConnect: true,
    backgroundMonitoring: true,
    dataRetentionDays: 30,
    enableDataExport: true
  },

  notificationConfig: {
    enabled: true,
    sound: true,
    vibration: true,
    quietHours: {
      enabled: false,
      startTime: '22:00',
      endTime: '08:00'
    }
  },

  isDefault: true
};

/**
 * 預設應用程式配置
 */
export const DEFAULT_APP_CONFIG: AppConfig = {
  version: '1.0.0',
  theme: 'auto',
  language: 'zh-TW',

  units: {
    temperature: 'celsius',
    power: 'watts',
    energy: 'wh'
  },

  ui: {
    showAdvancedInfo: false,
    chartUpdateInterval: 5,
    enableAnimations: true,
    keepScreenOn: false
  },

  security: {
    biometricAuth: false,
    autoLockMinutes: 5,
    allowScreenshots: true
  },

  debug: {
    enabled: false,
    logLevel: 'warn',
    saveLogsToFile: false,
    showPerformanceInfo: false
  },

  updatedAt: new Date().toISOString()
};

/**
 * 配置工具類
 */
export class ConfigUtils {
  /**
   * 驗證設備配置
   * @param config 設備配置
   * @returns 驗證結果
   */
  static validateDeviceConfig(config: Partial<DeviceConfig>): {
    isValid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];

    if (!config.name || config.name.trim().length === 0) {
      errors.push('設備名稱不能為空');
    }

    if (!config.deviceType) {
      errors.push('必須指定設備類型');
    }

    if (config.connectionMode === ConnectionMode.BLUETOOTH && !config.bluetoothAddress) {
      errors.push('藍牙連接模式需要指定 MAC 地址');
    }

    if (config.batterySpecs) {
      const specs = config.batterySpecs;
      if (specs.cellCount < 1 || specs.cellCount > 32) {
        errors.push('電芯串數必須在 1-32 之間');
      }
      if (specs.maxVoltage <= specs.minVoltage) {
        errors.push('最大電壓必須大於最小電壓');
      }
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * 生成設備配置 ID
   * @param name 設備名稱
   * @returns 配置 ID
   */
  static generateDeviceId(name: string): string {
    const timestamp = Date.now();
    const sanitizedName = name.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
    return `${sanitizedName}_${timestamp}`;
  }

  /**
   * 深度複製配置物件
   * @param config 原始配置
   * @returns 複製的配置
   */
  static deepCloneConfig<T>(config: T): T {
    return JSON.parse(JSON.stringify(config));
  }
}