import { injectable, inject } from 'tsyringe';
import { SERVICE_TOKENS } from '@services/ServiceContainer';
import { IBLEService } from '@services/interfaces/IBLEService';
import { IStorageService } from '@services/interfaces/IStorageService';
import { IDataService } from '@services/interfaces/IDataService';
import { BatteryData, ConnectionStatus } from '@domain/entities/BatteryData';
import { DeviceConfig } from '@domain/entities/DeviceConfig';

/**
 * 電池監控用例
 * 負責協調電池數據的讀取、處理和存儲
 */
@injectable()
export class MonitorBatteryUseCase {
  private monitoring = false;
  private monitoringInterval: NodeJS.Timeout | null = null;
  private currentConfig: DeviceConfig | null = null;

  constructor(
    @inject(SERVICE_TOKENS.BLE_SERVICE) private bleService: IBLEService,
    @inject(SERVICE_TOKENS.STORAGE_SERVICE) private storageService: IStorageService,
    @inject(SERVICE_TOKENS.DATA_SERVICE) private dataService: IDataService
  ) {}

  /**
   * 開始監控電池
   * @param config 設備配置
   */
  async startMonitoring(config: DeviceConfig): Promise<{ success: boolean; message: string }> {
    try {
      if (this.monitoring) {
        return { success: false, message: '監控已在運行中' };
      }

      this.currentConfig = config;
      console.log('🔋 開始電池監控...');

      // 嘗試連接 BMS
      const connected = await this.bleService.connect(config.bluetoothAddress || '');
      if (!connected) {
        return { success: false, message: 'BMS 連接失敗' };
      }

      // 喚醒 BMS
      await this.bleService.wakeBMS();

      // 開始定期讀取數據
      this.startPeriodicReading(config.protocolConfig.readInterval);

      this.monitoring = true;
      
      // 保存最後連接時間
      await this.storageService.saveConfig('lastConnectedDevice', {
        ...config,
        lastConnectedAt: new Date().toISOString()
      });

      return { success: true, message: '電池監控已啟動' };

    } catch (error) {
      console.error('❌ 啟動監控失敗:', error);
      return { success: false, message: `啟動監控失敗: ${error}` };
    }
  }

  /**
   * 停止監控電池
   */
  async stopMonitoring(): Promise<void> {
    try {
      console.log('⏹️ 停止電池監控...');

      this.monitoring = false;

      // 停止定期讀取
      if (this.monitoringInterval) {
        clearInterval(this.monitoringInterval);
        this.monitoringInterval = null;
      }

      // 斷開 BLE 連接
      await this.bleService.disconnect();

      this.currentConfig = null;
      console.log('✅ 電池監控已停止');

    } catch (error) {
      console.error('❌ 停止監控失敗:', error);
    }
  }

  /**
   * 立即讀取電池數據
   */
  async readBatteryDataNow(): Promise<BatteryData | null> {
    try {
      if (!this.bleService.isConnected()) {
        console.warn('⚠️ BMS 未連接');
        return null;
      }

      console.log('📊 讀取電池數據...');
      const rawData = await this.bleService.readBMSData();
      
      if (!rawData) {
        console.warn('⚠️ 無法讀取 BMS 數據');
        return null;
      }

      // 驗證數據
      const validation = this.dataService.validateBatteryData(rawData);
      if (!validation.isValid) {
        console.error('❌ 電池數據驗證失敗:', validation.errors);
        return null;
      }

      const batteryData = validation.sanitizedData!;

      // 保存到數據庫
      try {
        await this.storageService.saveBatteryData(batteryData);
      } catch (storageError) {
        console.error('⚠️ 保存數據失敗:', storageError);
        // 不影響數據讀取的返回
      }

      console.log('✅ 電池數據讀取成功');
      return batteryData;

    } catch (error) {
      console.error('❌ 讀取電池數據失敗:', error);
      return null;
    }
  }

  /**
   * 獲取監控狀態
   */
  getMonitoringStatus(): {
    isMonitoring: boolean;
    isConnected: boolean;
    currentConfig: DeviceConfig | null;
    connectionStats: any;
  } {
    return {
      isMonitoring: this.monitoring,
      isConnected: this.bleService.isConnected(),
      currentConfig: this.currentConfig,
      connectionStats: this.bleService.getConnectionStats()
    };
  }

  /**
   * 獲取電池歷史數據
   */
  async getBatteryHistory(
    timeRange?: { startTime: Date; endTime: Date },
    limit?: number
  ): Promise<BatteryData[]> {
    try {
      const pagination = limit ? { offset: 0, limit } : undefined;
      const history = await this.storageService.getBatteryHistory(timeRange, pagination);
      
      console.log(`📈 獲取歷史數據: ${history.length} 筆記錄`);
      return history;

    } catch (error) {
      console.error('❌ 獲取歷史數據失敗:', error);
      return [];
    }
  }

  /**
   * 獲取電池統計資訊
   */
  async getBatteryStats(days: number = 7): Promise<any> {
    try {
      const endTime = new Date();
      const startTime = new Date();
      startTime.setDate(startTime.getDate() - days);

      const historicalData = await this.storageService.getBatteryHistory({ startTime, endTime });
      
      if (historicalData.length === 0) {
        return null;
      }

      const stats = this.dataService.calculateBatteryStats(historicalData);
      
      console.log('📊 計算統計資訊完成');
      return {
        ...stats,
        dataCount: historicalData.length,
        timeRange: { startTime, endTime }
      };

    } catch (error) {
      console.error('❌ 計算統計資訊失敗:', error);
      return null;
    }
  }

  /**
   * 評估電池健康狀態
   */
  async assessBatteryHealth(): Promise<any> {
    try {
      const latestData = await this.storageService.getLatestBatteryData();
      if (!latestData) {
        return null;
      }

      const endTime = new Date();
      const startTime = new Date();
      startTime.setDate(startTime.getDate() - 30); // 過去 30 天

      const historicalData = await this.storageService.getBatteryHistory({ startTime, endTime });
      
      const healthAssessment = this.dataService.assessBatteryHealth(latestData, historicalData);
      
      console.log('💚 電池健康評估完成');
      return {
        ...healthAssessment,
        assessmentTime: new Date().toISOString(),
        dataCount: historicalData.length
      };

    } catch (error) {
      console.error('❌ 電池健康評估失敗:', error);
      return null;
    }
  }

  /**
   * 清理舊數據
   */
  async cleanupOldData(retentionDays: number = 30): Promise<void> {
    try {
      await this.storageService.cleanupOldData(retentionDays);
      console.log(`🧹 清理 ${retentionDays} 天前的舊數據完成`);
    } catch (error) {
      console.error('❌ 清理舊數據失敗:', error);
    }
  }

  /**
   * 匯出數據
   */
  async exportData(
    timeRange?: { startTime: Date; endTime: Date }
  ): Promise<string | null> {
    try {
      const exportedData = await this.storageService.exportData(timeRange);
      console.log('📤 數據匯出完成');
      return exportedData;
    } catch (error) {
      console.error('❌ 數據匯出失敗:', error);
      return null;
    }
  }

  // 私有方法

  /**
   * 開始定期讀取數據
   */
  private startPeriodicReading(intervalSeconds: number): void {
    this.monitoringInterval = setInterval(async () => {
      if (!this.monitoring) {
        return;
      }

      try {
        await this.readBatteryDataNow();
      } catch (error) {
        console.error('❌ 定期讀取數據失敗:', error);
        
        // 如果連續失敗多次，可能需要重新連接
        const stats = this.bleService.getConnectionStats();
        if (stats.errorCount > 5 && stats.successRate < 50) {
          console.warn('⚠️ 連接不穩定，嘗試重新連接...');
          await this.attemptReconnection();
        }
      }
    }, intervalSeconds * 1000);

    console.log(`⏰ 定期讀取已設置: ${intervalSeconds} 秒間隔`);
  }

  /**
   * 嘗試重新連接
   */
  private async attemptReconnection(): Promise<void> {
    if (!this.currentConfig) {
      return;
    }

    try {
      console.log('🔄 嘗試重新連接 BMS...');
      
      // 先斷開現有連接
      await this.bleService.disconnect();
      
      // 等待一段時間後重新連接
      await this.delay(3000);
      
      const connected = await this.bleService.connect(this.currentConfig.bluetoothAddress || '');
      if (connected) {
        await this.bleService.wakeBMS();
        console.log('✅ BMS 重新連接成功');
      } else {
        console.error('❌ BMS 重新連接失敗');
      }

    } catch (error) {
      console.error('❌ 重新連接過程出錯:', error);
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}