import { BatteryData } from '@domain/entities/BatteryData';
import { BatteryAlert, AlertRule } from '@domain/entities/AlertRule';

/**
 * 數據處理服務介面
 * 負責數據驗證、轉換、分析和警報檢查
 */
export interface IDataService {
  /**
   * 驗證電池數據的有效性
   * @param data 原始電池數據
   * @returns 驗證結果
   */
  validateBatteryData(data: any): {
    isValid: boolean;
    errors: string[];
    sanitizedData?: BatteryData;
  };

  /**
   * 將原始 BMS 響應轉換為標準化數據格式
   * @param rawData 來自 BMS 的原始數據
   * @returns 標準化的電池數據
   */
  transformBMSData(rawData: any): BatteryData;

  /**
   * 檢查警報條件
   * @param data 電池數據
   * @param rules 警報規則陣列
   * @returns 觸發的警報陣列
   */
  checkAlerts(data: BatteryData, rules: AlertRule[]): BatteryAlert[];

  /**
   * 計算電池統計資訊
   * @param historicalData 歷史數據陣列
   * @returns 統計資訊
   */
  calculateBatteryStats(historicalData: BatteryData[]): {
    averageVoltage: number;
    maxVoltage: number;
    minVoltage: number;
    averageCurrent: number;
    averageTemperature: number;
    totalEnergyConsumed: number; // Wh
    cycleCount: number;
    healthScore: number; // 0-100
  };

  /**
   * 估算剩餘使用時間
   * @param currentData 當前電池數據
   * @param historicalData 歷史數據（用於計算平均消耗）
   * @returns 估算時間（分鐘）
   */
  estimateRemainingTime(
    currentData: BatteryData,
    historicalData: BatteryData[]
  ): number | null;

  /**
   * 檢測電池健康狀態
   * @param data 電池數據
   * @param historicalData 歷史數據
   * @returns 健康狀態評估
   */
  assessBatteryHealth(
    data: BatteryData,
    historicalData: BatteryData[]
  ): {
    score: number; // 0-100
    status: 'excellent' | 'good' | 'fair' | 'poor' | 'critical';
    issues: string[];
    recommendations: string[];
  };

  /**
   * 計算功率和能量
   * @param voltage 電壓 (V)
   * @param current 電流 (A)
   * @param previousData 前一次數據（用於計算時間差）
   * @returns 功率和能量資訊
   */
  calculatePowerMetrics(
    voltage: number,
    current: number,
    previousData?: BatteryData
  ): {
    power: number; // W
    energyDelta?: number; // Wh (since last reading)
  };

  /**
   * 平滑數據（移除雜訊）
   * @param data 數據陣列
   * @param windowSize 平滑窗口大小
   * @returns 平滑後的數據
   */
  smoothData<T extends { timestamp: string; [key: string]: any }>(
    data: T[],
    windowSize: number
  ): T[];

  /**
   * 檢測數據異常
   * @param currentData 當前數據
   * @param historicalData 歷史數據
   * @returns 異常檢測結果
   */
  detectAnomalies(
    currentData: BatteryData,
    historicalData: BatteryData[]
  ): {
    hasAnomalies: boolean;
    anomalies: Array<{
      field: string;
      currentValue: number;
      expectedRange: { min: number; max: number };
      severity: 'low' | 'medium' | 'high';
    }>;
  };
}