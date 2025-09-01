import { injectable, inject } from 'tsyringe';
import { SERVICE_TOKENS } from '@services/ServiceContainer';
import { INotificationService } from '@services/interfaces/INotificationService';
import { IStorageService } from '@services/interfaces/IStorageService';
import { IDataService } from '@services/interfaces/IDataService';
import { BatteryData } from '@domain/entities/BatteryData';
import { BatteryAlert, AlertRule, DEFAULT_ALERT_RULES, AlertUtils } from '@domain/entities/AlertRule';

/**
 * 警報處理用例
 * 負責監控數據、檢查警報規則、發送通知和管理警報狀態
 */
@injectable()
export class HandleAlertsUseCase {
  private alertRules: AlertRule[] = [];
  private lastAlertTimes: Map<string, number> = new Map(); // 用於冷卻期管理
  private alertHistory: Map<string, BatteryAlert> = new Map(); // 警報歷史緩存

  constructor(
    @inject(SERVICE_TOKENS.NOTIFICATION_SERVICE) private notificationService: INotificationService,
    @inject(SERVICE_TOKENS.STORAGE_SERVICE) private storageService: IStorageService,
    @inject(SERVICE_TOKENS.DATA_SERVICE) private dataService: IDataService
  ) {
    this.initializeDefaultRules();
  }

  /**
   * 初始化預設警報規則
   */
  private async initializeDefaultRules(): Promise<void> {
    try {
      // 嘗試從存儲載入自訂規則
      const savedRules = await this.storageService.getConfig<AlertRule[]>('alertRules');
      
      if (savedRules && savedRules.length > 0) {
        this.alertRules = savedRules;
        console.log(`📋 載入 ${savedRules.length} 個自訂警報規則`);
      } else {
        // 使用預設規則
        this.alertRules = [...DEFAULT_ALERT_RULES];
        await this.storageService.saveConfig('alertRules', this.alertRules);
        console.log(`📋 初始化 ${this.alertRules.length} 個預設警報規則`);
      }
    } catch (error) {
      console.error('❌ 初始化警報規則失敗:', error);
      this.alertRules = [...DEFAULT_ALERT_RULES];
    }
  }

  /**
   * 處理新的電池數據並檢查警報
   * @param batteryData 最新電池數據
   */
  async processNewData(batteryData: BatteryData): Promise<void> {
    try {
      // 檢查所有啟用的警報規則
      const triggeredAlerts = this.dataService.checkAlerts(batteryData, this.alertRules);
      
      if (triggeredAlerts.length === 0) {
        return;
      }

      console.log(`🚨 檢測到 ${triggeredAlerts.length} 個警報`);

      // 處理每個觸發的警報
      for (const alert of triggeredAlerts) {
        await this.handleTriggeredAlert(alert);
      }

    } catch (error) {
      console.error('❌ 處理數據警報失敗:', error);
    }
  }

  /**
   * 處理觸發的警報
   */
  private async handleTriggeredAlert(alert: BatteryAlert): Promise<void> {
    try {
      const rule = this.alertRules.find(r => r.id === alert.ruleId);
      if (!rule) {
        console.warn(`⚠️ 找不到警報規則: ${alert.ruleId}`);
        return;
      }

      // 檢查冷卻期
      if (this.isInCooldown(alert.ruleId, rule.cooldownSeconds)) {
        console.log(`⏳ 警報在冷卻期內，跳過: ${rule.name}`);
        return;
      }

      // 保存警報記錄
      const alertId = await this.storageService.saveAlert(alert);
      alert.id = alertId;

      // 發送通知
      if (rule.sendNotification) {
        await this.sendAlertNotification(alert);
      }

      // 更新警報快取和冷卻時間
      this.alertHistory.set(alert.ruleId, alert);
      this.lastAlertTimes.set(alert.ruleId, Date.now());

      console.log(`🚨 處理警報完成: ${rule.name} (ID: ${alertId})`);

    } catch (error) {
      console.error('❌ 處理觸發警報失敗:', error);
    }
  }

  /**
   * 發送警報通知
   */
  private async sendAlertNotification(alert: BatteryAlert): Promise<void> {
    try {
      const notificationId = await this.notificationService.showAlert(alert);
      
      // 更新警報的通知 ID
      alert.notificationId = notificationId;
      if (alert.id) {
        // TODO: 更新數據庫中的通知 ID
      }

      console.log(`📱 警報通知已發送: ${alert.message}`);

    } catch (error) {
      console.error('❌ 發送警報通知失敗:', error);
    }
  }

  /**
   * 確認警報
   * @param alertId 警報 ID
   */
  async acknowledgeAlert(alertId: number): Promise<boolean> {
    try {
      // 從數據庫獲取警報
      const alerts = await this.storageService.getAlertHistory(
        undefined, 
        { offset: 0, limit: 1000 }
      );
      
      const alert = alerts.find(a => a.id === alertId);
      if (!alert) {
        console.warn(`⚠️ 找不到警報: ID ${alertId}`);
        return false;
      }

      if (alert.acknowledged) {
        console.log(`ℹ️ 警報已確認: ID ${alertId}`);
        return true;
      }

      // 更新警報狀態
      alert.acknowledged = true;
      alert.acknowledgedAt = new Date().toISOString();

      // TODO: 更新數據庫
      // await this.storageService.updateAlert(alert);

      // 取消通知
      if (alert.notificationId) {
        await this.notificationService.cancelAlert(alert.notificationId);
      }

      console.log(`✅ 警報已確認: ID ${alertId}`);
      return true;

    } catch (error) {
      console.error('❌ 確認警報失敗:', error);
      return false;
    }
  }

  /**
   * 解決警報
   * @param alertId 警報 ID
   */
  async resolveAlert(alertId: number): Promise<boolean> {
    try {
      const alerts = await this.storageService.getAlertHistory(
        undefined, 
        { offset: 0, limit: 1000 }
      );
      
      const alert = alerts.find(a => a.id === alertId);
      if (!alert) {
        console.warn(`⚠️ 找不到警報: ID ${alertId}`);
        return false;
      }

      if (alert.resolved) {
        console.log(`ℹ️ 警報已解決: ID ${alertId}`);
        return true;
      }

      // 更新警報狀態
      alert.resolved = true;
      alert.resolvedAt = new Date().toISOString();

      // 如果未確認，同時標記為已確認
      if (!alert.acknowledged) {
        alert.acknowledged = true;
        alert.acknowledgedAt = new Date().toISOString();
      }

      // TODO: 更新數據庫
      // await this.storageService.updateAlert(alert);

      // 取消通知
      if (alert.notificationId) {
        await this.notificationService.cancelAlert(alert.notificationId);
      }

      console.log(`✅ 警報已解決: ID ${alertId}`);
      return true;

    } catch (error) {
      console.error('❌ 解決警報失敗:', error);
      return false;
    }
  }

  /**
   * 獲取活躍警報列表
   */
  async getActiveAlerts(): Promise<BatteryAlert[]> {
    try {
      const oneHourAgo = new Date();
      oneHourAgo.setHours(oneHourAgo.getHours() - 1);

      const recentAlerts = await this.storageService.getAlertHistory(
        { startTime: oneHourAgo, endTime: new Date() },
        { offset: 0, limit: 100 }
      );

      // 過濾出未解決的警報
      const activeAlerts = recentAlerts.filter(alert => 
        !alert.resolved && !alert.acknowledged
      );

      console.log(`🚨 獲取活躍警報: ${activeAlerts.length} 個`);
      return activeAlerts;

    } catch (error) {
      console.error('❌ 獲取活躍警報失敗:', error);
      return [];
    }
  }

  /**
   * 獲取警報歷史
   */
  async getAlertHistory(
    days: number = 7,
    limit: number = 100
  ): Promise<BatteryAlert[]> {
    try {
      const endTime = new Date();
      const startTime = new Date();
      startTime.setDate(startTime.getDate() - days);

      const history = await this.storageService.getAlertHistory(
        { startTime, endTime },
        { offset: 0, limit }
      );

      console.log(`📊 獲取警報歷史: ${history.length} 筆記錄`);
      return history;

    } catch (error) {
      console.error('❌ 獲取警報歷史失敗:', error);
      return [];
    }
  }

  /**
   * 獲取警報統計
   */
  async getAlertStats(days: number = 7): Promise<{
    totalAlerts: number;
    criticalAlerts: number;
    warningAlerts: number;
    infoAlerts: number;
    acknowledgedAlerts: number;
    unresolvedAlerts: number;
    alertsByType: Record<string, number>;
  } | null> {
    try {
      const history = await this.getAlertHistory(days);
      
      if (history.length === 0) {
        return null;
      }

      const stats = {
        totalAlerts: history.length,
        criticalAlerts: history.filter(a => a.severity === 'critical').length,
        warningAlerts: history.filter(a => a.severity === 'warning').length,
        infoAlerts: history.filter(a => a.severity === 'info').length,
        acknowledgedAlerts: history.filter(a => a.acknowledged).length,
        unresolvedAlerts: history.filter(a => !a.resolved).length,
        alertsByType: {} as Record<string, number>
      };

      // 統計各類型警報數量
      for (const alert of history) {
        stats.alertsByType[alert.type] = (stats.alertsByType[alert.type] || 0) + 1;
      }

      console.log('📊 警報統計計算完成');
      return stats;

    } catch (error) {
      console.error('❌ 獲取警報統計失敗:', error);
      return null;
    }
  }

  /**
   * 更新警報規則
   * @param rules 新的警報規則列表
   */
  async updateAlertRules(rules: AlertRule[]): Promise<boolean> {
    try {
      // 驗證規則
      for (const rule of rules) {
        if (!rule.id || !rule.name || !rule.field) {
          throw new Error(`無效的警報規則: ${rule.id}`);
        }
      }

      this.alertRules = [...rules];
      await this.storageService.saveConfig('alertRules', this.alertRules);

      // 清空冷卻期快取（因為規則可能已更改）
      this.lastAlertTimes.clear();

      console.log(`📋 警報規則已更新: ${rules.length} 個規則`);
      return true;

    } catch (error) {
      console.error('❌ 更新警報規則失敗:', error);
      return false;
    }
  }

  /**
   * 獲取當前警報規則
   */
  getAlertRules(): AlertRule[] {
    return [...this.alertRules];
  }

  /**
   * 測試警報規則
   * @param rule 要測試的規則
   * @param testData 測試數據
   */
  testAlertRule(rule: AlertRule, testData: BatteryData): BatteryAlert[] {
    try {
      const alerts = this.dataService.checkAlerts(testData, [rule]);
      console.log(`🧪 測試警報規則: ${alerts.length > 0 ? '觸發' : '未觸發'}`);
      return alerts;
    } catch (error) {
      console.error('❌ 測試警報規則失敗:', error);
      return [];
    }
  }

  /**
   * 清空所有通知
   */
  async clearAllNotifications(): Promise<void> {
    try {
      await this.notificationService.cancelAllAlerts();
      console.log('🧹 已清空所有通知');
    } catch (error) {
      console.error('❌ 清空通知失敗:', error);
    }
  }

  // 私有工具方法

  /**
   * 檢查是否在冷卻期內
   */
  private isInCooldown(ruleId: string, cooldownSeconds: number): boolean {
    const lastAlertTime = this.lastAlertTimes.get(ruleId);
    if (!lastAlertTime) {
      return false;
    }

    const now = Date.now();
    const cooldownMs = cooldownSeconds * 1000;
    return (now - lastAlertTime) < cooldownMs;
  }
}