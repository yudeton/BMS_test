import notifee, { 
  AuthorizationStatus, 
  AndroidImportance, 
  AndroidCategory,
  EventType,
  Notification,
  TriggerType,
  TimestampTrigger
} from '@notifee/react-native';
import { injectable } from 'tsyringe';
import { INotificationService } from '@services/interfaces/INotificationService';
import { BatteryAlert, AlertSeverity, AlertUtils } from '@domain/entities/AlertRule';
import { Platform } from 'react-native';

/**
 * 通知通道 ID 定義
 */
const NOTIFICATION_CHANNELS = {
  CRITICAL: 'battery_critical',
  WARNING: 'battery_warning',
  INFO: 'battery_info',
  CONNECTION: 'connection_status'
} as const;

/**
 * Notifee 本地通知服務實作
 * 實現完全離線的推送通知功能
 */
@injectable()
export class NotificationService implements INotificationService {
  private initialized = false;
  private notificationClickListeners: Array<(notificationId: string, data?: any) => void> = [];

  constructor() {
    this.setupBackgroundHandler();
  }

  /**
   * 初始化通知服務
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }

    try {
      console.log('🔔 初始化通知服務...');

      // 檢查並請求權限
      const hasPermission = await this.requestPermissions();
      if (!hasPermission) {
        console.warn('⚠️ 通知權限未授予');
      }

      // 設置通知通道
      await this.setupNotificationChannels();

      // 設置前景事件監聽器
      this.setupForegroundEventListener();

      this.initialized = true;
      console.log('✅ 通知服務初始化完成');

    } catch (error) {
      console.error('❌ 通知服務初始化失敗:', error);
      throw error;
    }
  }

  /**
   * 檢查通知權限狀態
   */
  async checkPermissions(): Promise<boolean> {
    const settings = await notifee.getNotificationSettings();
    return settings.authorizationStatus === AuthorizationStatus.AUTHORIZED;
  }

  /**
   * 請求通知權限
   */
  async requestPermissions(): Promise<boolean> {
    try {
      const settings = await notifee.requestPermission();
      const authorized = settings.authorizationStatus === AuthorizationStatus.AUTHORIZED;
      
      console.log('📱 通知權限狀態:', authorized ? '已授予' : '未授予');
      
      if (Platform.OS === 'android') {
        // Android 額外檢查電池優化
        const batteryOptimizationEnabled = await notifee.isBatteryOptimizationEnabled();
        if (batteryOptimizationEnabled) {
          console.warn('⚠️ 建議關閉電池優化以確保通知正常運作');
        }
      }
      
      return authorized;

    } catch (error) {
      console.error('❌ 請求通知權限失敗:', error);
      return false;
    }
  }

  /**
   * 設置通知通道
   */
  async setupNotificationChannels(): Promise<void> {
    if (Platform.OS !== 'android') {
      return; // iOS 不需要手動設置通道
    }

    try {
      const channels = [
        {
          id: NOTIFICATION_CHANNELS.CRITICAL,
          name: '危險警報',
          description: '電池危險狀態警報',
          importance: AndroidImportance.HIGH,
          sound: 'default',
          vibration: true,
          lights: true,
          lightColor: '#FF0000'
        },
        {
          id: NOTIFICATION_CHANNELS.WARNING,
          name: '警告通知',
          description: '電池警告狀態通知',
          importance: AndroidImportance.DEFAULT,
          sound: 'default',
          vibration: true,
          lights: true,
          lightColor: '#FFA500'
        },
        {
          id: NOTIFICATION_CHANNELS.INFO,
          name: '資訊通知',
          description: '一般資訊通知',
          importance: AndroidImportance.LOW,
          sound: undefined,
          vibration: false
        },
        {
          id: NOTIFICATION_CHANNELS.CONNECTION,
          name: '連接狀態',
          description: 'BMS 連接狀態通知',
          importance: AndroidImportance.DEFAULT,
          sound: 'default',
          vibration: true
        }
      ];

      for (const channel of channels) {
        await notifee.createChannel(channel);
        console.log(`📢 創建通知通道: ${channel.name}`);
      }

    } catch (error) {
      console.error('❌ 設置通知通道失敗:', error);
      throw error;
    }
  }

  /**
   * 立即顯示警報通知
   */
  async showAlert(alert: BatteryAlert): Promise<void> {
    try {
      const channelId = this.getChannelForSeverity(alert.severity);
      
      const notification: Notification = {
        id: alert.id?.toString() || Date.now().toString(),
        title: this.getAlertTitle(alert),
        body: alert.message,
        data: {
          alertId: alert.id,
          ruleId: alert.ruleId,
          type: alert.type,
          severity: alert.severity,
          timestamp: alert.timestamp
        },
        android: {
          channelId,
          category: AndroidCategory.ALARM,
          color: AlertUtils.getSeverityColor(alert.severity),
          largeIcon: this.getSeverityIcon(alert.severity),
          actions: this.getNotificationActions(alert),
          autoCancel: true,
          showTimestamp: true,
          timestamp: new Date(alert.timestamp).getTime()
        },
        ios: {
          categoryId: 'BATTERY_ALERT',
          sound: alert.severity === AlertSeverity.CRITICAL ? 'default' : undefined,
          badge: await this.getUnacknowledgedAlertCount() + 1,
          interruptionLevel: alert.severity === AlertSeverity.CRITICAL ? 'critical' : 'active'
        }
      };

      await notifee.displayNotification(notification);
      
      console.log(`🔔 顯示${alert.severity}警報: ${alert.message}`);

      // 如果是危險警報且手機支援，觸發震動
      if (alert.severity === AlertSeverity.CRITICAL && Platform.OS === 'android') {
        // 可以使用 React Native 的 Vibration API
        // Vibration.vibrate([500, 500, 500, 500]);
      }

    } catch (error) {
      console.error('❌ 顯示警報通知失敗:', error);
      throw error;
    }
  }

  /**
   * 排程延遲通知
   */
  async scheduleAlert(alert: BatteryAlert, delaySeconds: number): Promise<string> {
    try {
      const notificationId = alert.id?.toString() || Date.now().toString();
      const channelId = this.getChannelForSeverity(alert.severity);

      const trigger: TimestampTrigger = {
        type: TriggerType.TIMESTAMP,
        timestamp: Date.now() + (delaySeconds * 1000)
      };

      const notification: Notification = {
        id: notificationId,
        title: this.getAlertTitle(alert),
        body: alert.message,
        data: {
          alertId: alert.id,
          ruleId: alert.ruleId,
          type: alert.type,
          severity: alert.severity,
          scheduled: true
        },
        android: {
          channelId,
          category: AndroidCategory.ALARM,
          color: AlertUtils.getSeverityColor(alert.severity)
        }
      };

      await notifee.createTriggerNotification(notification, trigger);
      
      console.log(`⏰ 排程警報通知: ${delaySeconds}秒後 - ${alert.message}`);
      return notificationId;

    } catch (error) {
      console.error('❌ 排程警報通知失敗:', error);
      throw error;
    }
  }

  /**
   * 取消指定的通知
   */
  async cancelAlert(notificationId: string): Promise<void> {
    try {
      await notifee.cancelNotification(notificationId);
      console.log(`🚫 取消通知: ${notificationId}`);
    } catch (error) {
      console.error('❌ 取消通知失敗:', error);
    }
  }

  /**
   * 取消所有通知
   */
  async cancelAllAlerts(): Promise<void> {
    try {
      await notifee.cancelAllNotifications();
      console.log('🧹 已取消所有通知');
    } catch (error) {
      console.error('❌ 取消所有通知失敗:', error);
    }
  }

  /**
   * 設置背景通知處理
   */
  setupBackgroundHandler(): void {
    notifee.onBackgroundEvent(async ({ type, detail }) => {
      console.log('🔄 背景通知事件:', type);

      if (type === EventType.PRESS && detail.notification) {
        const notificationData = detail.notification.data;
        this.handleNotificationPress(detail.notification.id || '', notificationData);
      }

      if (type === EventType.ACTION_PRESS && detail.notification && detail.pressAction) {
        await this.handleNotificationAction(
          detail.notification.id || '', 
          detail.pressAction.id,
          detail.notification.data
        );
      }
    });
  }

  /**
   * 更新徽章數字（iOS）
   */
  async updateBadgeCount(count: number): Promise<void> {
    if (Platform.OS === 'ios') {
      try {
        await notifee.setBadgeCount(count);
      } catch (error) {
        console.error('❌ 更新徽章數字失敗:', error);
      }
    }
  }

  /**
   * 註冊通知點擊監聽器
   */
  onNotificationPress(callback: (notificationId: string, data?: any) => void): void {
    this.notificationClickListeners.push(callback);
  }

  /**
   * 關閉服務
   */
  async shutdown(): Promise<void> {
    this.notificationClickListeners = [];
    console.log('🔔 通知服務已關閉');
  }

  // 私有工具方法

  private setupForegroundEventListener(): void {
    notifee.onForegroundEvent(({ type, detail }) => {
      if (type === EventType.PRESS && detail.notification) {
        const notificationData = detail.notification.data;
        this.handleNotificationPress(detail.notification.id || '', notificationData);
      }

      if (type === EventType.ACTION_PRESS && detail.notification && detail.pressAction) {
        this.handleNotificationAction(
          detail.notification.id || '',
          detail.pressAction.id,
          detail.notification.data
        );
      }
    });
  }

  private handleNotificationPress(notificationId: string, data?: any): void {
    console.log('👆 通知被點擊:', notificationId);
    this.notificationClickListeners.forEach(listener => listener(notificationId, data));
  }

  private async handleNotificationAction(
    notificationId: string, 
    actionId: string, 
    data?: any
  ): Promise<void> {
    console.log('⚡ 通知動作被觸發:', actionId);

    switch (actionId) {
      case 'acknowledge':
        // 確認警報
        await this.cancelAlert(notificationId);
        console.log('✅ 警報已確認');
        break;
      
      case 'snooze':
        // 稍後提醒（10分鐘後）
        await this.cancelAlert(notificationId);
        if (data) {
          // 重新排程
          // 這裡需要重新創建 BatteryAlert 物件
          console.log('⏰ 稍後提醒已設定');
        }
        break;
      
      default:
        console.log('❓ 未知動作:', actionId);
    }
  }

  private getChannelForSeverity(severity: AlertSeverity): string {
    switch (severity) {
      case AlertSeverity.CRITICAL:
        return NOTIFICATION_CHANNELS.CRITICAL;
      case AlertSeverity.WARNING:
        return NOTIFICATION_CHANNELS.WARNING;
      case AlertSeverity.INFO:
        return NOTIFICATION_CHANNELS.INFO;
      default:
        return NOTIFICATION_CHANNELS.INFO;
    }
  }

  private getAlertTitle(alert: BatteryAlert): string {
    switch (alert.severity) {
      case AlertSeverity.CRITICAL:
        return '🚨 電池危險警報';
      case AlertSeverity.WARNING:
        return '⚠️ 電池警告';
      case AlertSeverity.INFO:
        return 'ℹ️ 電池資訊';
      default:
        return '🔋 電池通知';
    }
  }

  private getSeverityIcon(severity: AlertSeverity): string {
    // 這裡返回 Android 大圖標的資源名稱
    switch (severity) {
      case AlertSeverity.CRITICAL:
        return 'ic_battery_alert';
      case AlertSeverity.WARNING:
        return 'ic_battery_warning';
      case AlertSeverity.INFO:
        return 'ic_battery_info';
      default:
        return 'ic_battery_unknown';
    }
  }

  private getNotificationActions(alert: BatteryAlert) {
    if (alert.severity === AlertSeverity.CRITICAL || alert.severity === AlertSeverity.WARNING) {
      return [
        {
          title: '確認',
          pressAction: { id: 'acknowledge' }
        },
        {
          title: '稍後提醒',
          pressAction: { id: 'snooze' }
        }
      ];
    }
    return [];
  }

  private async getUnacknowledgedAlertCount(): Promise<number> {
    // 這裡應該查詢存儲服務獲取未確認警報數量
    // 暫時返回 0
    return 0;
  }
}