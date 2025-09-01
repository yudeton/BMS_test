import { BatteryAlert } from '@domain/entities/AlertRule';

/**
 * 通知服務介面
 * 負責本地推送通知管理（使用 Notifee，完全離線）
 */
export interface INotificationService {
  /**
   * 初始化通知服務
   * 設置通知權限和通道
   */
  initialize(): Promise<void>;

  /**
   * 檢查通知權限狀態
   */
  checkPermissions(): Promise<boolean>;

  /**
   * 請求通知權限
   */
  requestPermissions(): Promise<boolean>;

  /**
   * 設置通知通道（Android）
   */
  setupNotificationChannels(): Promise<void>;

  /**
   * 立即顯示警報通知
   * @param alert 警報資訊
   */
  showAlert(alert: BatteryAlert): Promise<void>;

  /**
   * 排程延遲通知
   * @param alert 警報資訊
   * @param delaySeconds 延遲秒數
   */
  scheduleAlert(alert: BatteryAlert, delaySeconds: number): Promise<string>;

  /**
   * 取消指定的通知
   * @param notificationId 通知 ID
   */
  cancelAlert(notificationId: string): Promise<void>;

  /**
   * 取消所有通知
   */
  cancelAllAlerts(): Promise<void>;

  /**
   * 設置背景通知處理
   * 當 App 在背景時處理通知點擊
   */
  setupBackgroundHandler(): void;

  /**
   * 更新徽章數字（iOS）
   * @param count 徽章數字
   */
  updateBadgeCount(count: number): Promise<void>;

  /**
   * 註冊通知點擊監聽器
   * @param callback 點擊回調函數
   */
  onNotificationPress(callback: (notificationId: string, data?: any) => void): void;
}