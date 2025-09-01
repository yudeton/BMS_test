/**
 * 連接狀態枚舉
 */
export enum ConnectionStatus {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  ERROR = 'error',
  RECONNECTING = 'reconnecting'
}

/**
 * 電流方向枚舉
 */
export enum CurrentDirection {
  CHARGING = 'charging',      // 充電
  DISCHARGING = 'discharging', // 放電
  IDLE = 'idle'               // 靜止
}

/**
 * 電池數據實體
 * 標準化的電池監控數據格式
 */
export interface BatteryData {
  /** 數據記錄 ID（數據庫主鍵） */
  id?: number;

  /** 時間戳（ISO 8601 格式） */
  timestamp: string;

  /** 連接狀態 */
  connectionStatus: ConnectionStatus;

  /** 總電壓 (V) */
  totalVoltage: number;

  /** 電流 (A) - 正值表示放電，負值表示充電 */
  current: number;

  /** 電流方向 */
  currentDirection: CurrentDirection;

  /** 功率 (W) - 計算值：電壓 × 電流 */
  power: number;

  /** 電量百分比 (%) */
  soc: number;

  /** 電芯電壓陣列 (V) */
  cells: number[];

  /** 溫度陣列 (°C) - 多個溫度感測器 */
  temperatures: number[];

  /** 平均溫度 (°C) */
  averageTemperature: number;

  /** MOSFET 狀態（可選） */
  mosfetStatus?: {
    chargingEnabled: boolean;
    dischargingEnabled: boolean;
  };

  /** 故障狀態（可選） */
  faultStatus?: {
    hasFaults: boolean;
    faultCodes: number[];
    faultDescriptions: string[];
  };

  /** 數據品質指標 */
  quality: {
    /** 數據來源 */
    source: 'ble' | 'cached' | 'estimated';
    
    /** CRC 驗證狀態 */
    crcValid: boolean;
    
    /** 信號強度（BLE RSSI） */
    signalStrength?: number;
    
    /** 數據完整性評分 (0-100) */
    completenessScore: number;
  };

  /** 統計資訊 */
  stats?: {
    /** 自上次重置以來的讀取次數 */
    readCount: number;
    
    /** 錯誤次數 */
    errorCount: number;
    
    /** 成功率 (%) */
    successRate: number;
  };
}

/**
 * 電池數據建構器
 * 提供便利的數據創建方法
 */
export class BatteryDataBuilder {
  private data: Partial<BatteryData> = {};

  constructor() {
    this.data.timestamp = new Date().toISOString();
    this.data.connectionStatus = ConnectionStatus.DISCONNECTED;
    this.data.currentDirection = CurrentDirection.IDLE;
    this.data.cells = [];
    this.data.temperatures = [];
    this.data.quality = {
      source: 'ble',
      crcValid: false,
      completenessScore: 0
    };
  }

  withTimestamp(timestamp: string): BatteryDataBuilder {
    this.data.timestamp = timestamp;
    return this;
  }

  withConnectionStatus(status: ConnectionStatus): BatteryDataBuilder {
    this.data.connectionStatus = status;
    return this;
  }

  withVoltage(voltage: number): BatteryDataBuilder {
    this.data.totalVoltage = voltage;
    return this;
  }

  withCurrent(current: number, direction?: CurrentDirection): BatteryDataBuilder {
    this.data.current = current;
    if (direction) {
      this.data.currentDirection = direction;
    } else {
      // 自動判斷電流方向
      if (current > 0.1) {
        this.data.currentDirection = CurrentDirection.DISCHARGING;
      } else if (current < -0.1) {
        this.data.currentDirection = CurrentDirection.CHARGING;
      } else {
        this.data.currentDirection = CurrentDirection.IDLE;
      }
    }
    return this;
  }

  withSOC(soc: number): BatteryDataBuilder {
    this.data.soc = Math.max(0, Math.min(100, soc)); // 限制在 0-100
    return this;
  }

  withCells(cells: number[]): BatteryDataBuilder {
    this.data.cells = [...cells];
    return this;
  }

  withTemperatures(temperatures: number[]): BatteryDataBuilder {
    this.data.temperatures = [...temperatures];
    this.data.averageTemperature = temperatures.length > 0 
      ? temperatures.reduce((sum, temp) => sum + temp, 0) / temperatures.length
      : 0;
    return this;
  }

  withQuality(quality: Partial<BatteryData['quality']>): BatteryDataBuilder {
    this.data.quality = { 
      source: quality.source || this.data.quality.source,
      crcValid: quality.crcValid !== undefined ? quality.crcValid : this.data.quality.crcValid,
      signalStrength: quality.signalStrength || this.data.quality.signalStrength,
      completenessScore: quality.completenessScore !== undefined ? quality.completenessScore : this.data.quality.completenessScore
    };
    return this;
  }

  build(): BatteryData {
    // 計算功率
    if (this.data.totalVoltage && this.data.current) {
      this.data.power = this.data.totalVoltage * this.data.current;
    } else {
      this.data.power = 0;
    }

    // 驗證必要欄位
    if (!this.data.totalVoltage || !this.data.current !== undefined || !this.data.soc) {
      throw new Error('Missing required battery data fields');
    }

    return this.data as BatteryData;
  }
}

/**
 * 電池數據驗證工具
 */
export class BatteryDataValidator {
  /**
   * 驗證電池數據的有效性
   */
  static validate(data: Partial<BatteryData>): {
    isValid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];

    // 檢查必要欄位
    if (!data.timestamp) errors.push('Missing timestamp');
    if (data.totalVoltage === undefined) errors.push('Missing total voltage');
    if (data.current === undefined) errors.push('Missing current');
    if (data.soc === undefined) errors.push('Missing SOC');

    // 檢查數值範圍
    if (data.totalVoltage !== undefined) {
      if (data.totalVoltage < 0 || data.totalVoltage > 100) {
        errors.push('Total voltage out of range (0-100V)');
      }
    }

    if (data.soc !== undefined) {
      if (data.soc < 0 || data.soc > 100) {
        errors.push('SOC out of range (0-100%)');
      }
    }

    if (data.temperatures && data.temperatures.length > 0) {
      const invalidTemps = data.temperatures.filter(temp => temp < -40 || temp > 85);
      if (invalidTemps.length > 0) {
        errors.push('Temperature out of range (-40°C to 85°C)');
      }
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }
}