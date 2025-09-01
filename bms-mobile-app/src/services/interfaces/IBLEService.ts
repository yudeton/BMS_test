import { BatteryData, ConnectionStatus } from '@domain/entities/BatteryData';

/**
 * BLE 藍牙服務介面
 * 負責與 DALY BMS 設備的藍牙通訊
 */
export interface IBLEService {
  /**
   * 連接到指定的 BMS 設備
   * @param macAddress BMS 設備的 MAC 地址
   * @returns 連接是否成功
   */
  connect(macAddress: string): Promise<boolean>;

  /**
   * 斷開與 BMS 設備的連接
   */
  disconnect(): Promise<void>;

  /**
   * 檢查當前連接狀態
   */
  isConnected(): boolean;

  /**
   * 讀取 BMS 數據
   * @returns 電池數據或 null（如果讀取失敗）
   */
  readBMSData(): Promise<BatteryData | null>;

  /**
   * 喚醒 BMS 設備（發送喚醒命令）
   */
  wakeBMS(): Promise<void>;

  /**
   * 獲取連接統計資訊
   */
  getConnectionStats(): {
    connected: boolean;
    macAddress: string | null;
    readCount: number;
    errorCount: number;
    lastReadTime: number | null;
    successRate: number;
  };

  /**
   * 註冊連接狀態變化監聽器
   * @param callback 狀態變化回調函數
   */
  onConnectionStatusChange(callback: (status: ConnectionStatus) => void): void;

  /**
   * 註冊數據更新監聽器
   * @param callback 數據更新回調函數
   */
  onDataUpdate(callback: (data: BatteryData) => void): void;

  /**
   * 取消所有監聽器
   */
  removeAllListeners(): void;
}