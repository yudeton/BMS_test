import { BatteryData } from '@domain/entities/BatteryData';
import { BatteryAlert } from '@domain/entities/AlertRule';
import { DeviceConfig } from '@domain/entities/DeviceConfig';

/**
 * 時間範圍查詢參數
 */
export interface TimeRange {
  startTime: Date;
  endTime: Date;
}

/**
 * 分頁查詢參數
 */
export interface PaginationOptions {
  offset: number;
  limit: number;
}

/**
 * 數據存儲服務介面
 * 實現分層存儲：AsyncStorage（配置）+ SQLite（結構化數據）
 */
export interface IStorageService {
  // ========== AsyncStorage 層（簡單配置） ==========
  
  /**
   * 保存配置資料
   * @param key 配置鍵
   * @param value 配置值
   */
  saveConfig<T>(key: string, value: T): Promise<void>;

  /**
   * 讀取配置資料
   * @param key 配置鍵
   * @returns 配置值或 null
   */
  getConfig<T>(key: string): Promise<T | null>;

  /**
   * 刪除配置
   * @param key 配置鍵
   */
  removeConfig(key: string): Promise<void>;

  /**
   * 清空所有配置
   */
  clearAllConfig(): Promise<void>;

  // ========== SQLite 層（結構化數據） ==========

  /**
   * 初始化數據庫
   * 創建必要的表格
   */
  initializeDatabase(): Promise<void>;

  /**
   * 保存電池數據
   * @param data 電池數據
   * @returns 記錄 ID
   */
  saveBatteryData(data: BatteryData): Promise<number>;

  /**
   * 查詢電池歷史數據
   * @param timeRange 時間範圍
   * @param pagination 分頁選項
   * @returns 電池數據陣列
   */
  getBatteryHistory(
    timeRange?: TimeRange,
    pagination?: PaginationOptions
  ): Promise<BatteryData[]>;

  /**
   * 獲取最新的電池數據
   * @returns 最新電池數據或 null
   */
  getLatestBatteryData(): Promise<BatteryData | null>;

  /**
   * 保存警報記錄
   * @param alert 警報資訊
   * @returns 記錄 ID
   */
  saveAlert(alert: BatteryAlert): Promise<number>;

  /**
   * 查詢警報歷史
   * @param timeRange 時間範圍
   * @param pagination 分頁選項
   * @returns 警報陣列
   */
  getAlertHistory(
    timeRange?: TimeRange,
    pagination?: PaginationOptions
  ): Promise<BatteryAlert[]>;

  /**
   * 清理舊數據
   * @param olderThanDays 保留天數
   */
  cleanupOldData(olderThanDays: number): Promise<void>;

  /**
   * 獲取存儲統計資訊
   */
  getStorageStats(): Promise<{
    batteryDataCount: number;
    alertCount: number;
    databaseSize: number; // bytes
    oldestRecord: Date | null;
    newestRecord: Date | null;
  }>;

  /**
   * 匯出數據（JSON 格式）
   * @param timeRange 時間範圍
   * @returns JSON 字串
   */
  exportData(timeRange?: TimeRange): Promise<string>;

  /**
   * 關閉數據庫連接
   */
  closeDatabase(): Promise<void>;
}