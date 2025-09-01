import { observable, action, computed, reaction } from 'mobx';
import { BaseViewModel } from './BaseViewModel';
import { MonitorBatteryUseCase } from '@domain/usecases/MonitorBatteryUseCase';
import { HandleAlertsUseCase } from '@domain/usecases/HandleAlertsUseCase';
import { BatteryData, ConnectionStatus } from '@domain/entities/BatteryData';
import { BatteryAlert } from '@domain/entities/AlertRule';
import { DeviceConfig, DEFAULT_DEVICE_CONFIG } from '@domain/entities/DeviceConfig';

/**
 * 儀表板 ViewModel
 * 負責儀表板畫面的狀態管理和業務邏輯
 */
export class DashboardViewModel extends BaseViewModel {
  // 電池數據狀態
  @observable batteryData: BatteryData | null = null;
  @observable isMonitoring: boolean = false;
  @observable connectionStatus: ConnectionStatus = ConnectionStatus.DISCONNECTED;
  @observable lastUpdateTime: Date | null = null;

  // 警報狀態
  @observable activeAlerts: BatteryAlert[] = [];
  @observable alertCount: number = 0;

  // 統計數據
  @observable batteryStats: any = null;
  @observable healthAssessment: any = null;

  // 配置
  @observable deviceConfig: DeviceConfig | null = null;

  // 自動更新定時器
  private updateTimer: NodeJS.Timeout | null = null;
  private lastOperation: (() => Promise<void>) | null = null;

  constructor(
    private monitorBatteryUseCase: MonitorBatteryUseCase,
    private handleAlertsUseCase: HandleAlertsUseCase
  ) {
    super();
    
    this.setupAutoUpdates();
    this.loadInitialData();
  }

  /**
   * 載入初始數據
   */
  private async loadInitialData(): Promise<void> {
    await this.executeAsync(async () => {
      // 載入設備配置
      await this.loadDeviceConfig();
      
      // 載入最新電池數據
      await this.loadLatestBatteryData();
      
      // 載入活躍警報
      await this.loadActiveAlerts();
      
      // 載入統計數據
      await this.loadBatteryStats();
      
      console.log('📊 儀表板初始數據載入完成');
    }, '載入儀表板數據失敗');
  }

  /**
   * 開始監控
   */
  @action
  async startMonitoring(): Promise<void> {
    this.lastOperation = () => this.startMonitoring();
    
    await this.executeAsync(async () => {
      if (!this.deviceConfig) {
        throw new Error('設備配置未設定');
      }

      const result = await this.monitorBatteryUseCase.startMonitoring(this.deviceConfig);
      
      if (!result.success) {
        throw new Error(result.message);
      }

      this.isMonitoring = true;
      this.connectionStatus = ConnectionStatus.CONNECTED;
      
      console.log('🔋 電池監控已啟動');
    }, '啟動監控失敗');
  }

  /**
   * 停止監控
   */
  @action
  async stopMonitoring(): Promise<void> {
    await this.executeAsync(async () => {
      await this.monitorBatteryUseCase.stopMonitoring();
      
      this.isMonitoring = false;
      this.connectionStatus = ConnectionStatus.DISCONNECTED;
      
      console.log('⏹️ 電池監控已停止');
    }, '停止監控失敗');
  }

  /**
   * 手動讀取電池數據
   */
  @action
  async refreshBatteryData(): Promise<void> {
    this.lastOperation = () => this.refreshBatteryData();
    
    await this.executeAsync(async () => {
      const data = await this.monitorBatteryUseCase.readBatteryDataNow();
      
      if (data) {
        this.batteryData = data;
        this.lastUpdateTime = new Date();
        
        // 檢查警報
        await this.handleAlertsUseCase.processNewData(data);
        await this.loadActiveAlerts();
        
        console.log('🔄 電池數據已刷新');
      }
    }, '讀取電池數據失敗');
  }

  /**
   * 確認警報
   */
  @action
  async acknowledgeAlert(alertId: number): Promise<void> {
    await this.executeAsync(async () => {
      const success = await this.handleAlertsUseCase.acknowledgeAlert(alertId);
      
      if (success) {
        // 從活躍警報列表中移除
        this.activeAlerts = this.activeAlerts.filter(alert => alert.id !== alertId);
        this.alertCount = this.activeAlerts.length;
        
        console.log(`✅ 警報已確認: ID ${alertId}`);
      } else {
        throw new Error('確認警報失敗');
      }
    }, '確認警報失敗');
  }

  /**
   * 載入設備配置
   */
  private async loadDeviceConfig(): Promise<void> {
    // 暫時使用預設配置，後續從存儲載入
    this.deviceConfig = {
      ...DEFAULT_DEVICE_CONFIG,
      id: 'default',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
  }

  /**
   * 載入最新電池數據
   */
  @action
  private async loadLatestBatteryData(): Promise<void> {
    // 這裡可以從用例獲取最新數據
    const monitoringStatus = this.monitorBatteryUseCase.getMonitoringStatus();
    this.isMonitoring = monitoringStatus.isMonitoring;
    this.connectionStatus = monitoringStatus.isConnected 
      ? ConnectionStatus.CONNECTED 
      : ConnectionStatus.DISCONNECTED;
  }

  /**
   * 載入活躍警報
   */
  @action
  private async loadActiveAlerts(): Promise<void> {
    this.activeAlerts = await this.handleAlertsUseCase.getActiveAlerts();
    this.alertCount = this.activeAlerts.length;
  }

  /**
   * 載入電池統計
   */
  @action
  private async loadBatteryStats(): Promise<void> {
    this.batteryStats = await this.monitorBatteryUseCase.getBatteryStats(7);
    this.healthAssessment = await this.monitorBatteryUseCase.assessBatteryHealth();
  }

  /**
   * 設置自動更新
   */
  private setupAutoUpdates(): void {
    // 每 30 秒更新一次儀表板數據（如果在監控中）
    this.updateTimer = setInterval(async () => {
      if (this.isMonitoring && !this.isLoading) {
        await this.refreshDashboardData();
      }
    }, 30000);

    // 監聽監控狀態變化
    reaction(
      () => this.isMonitoring,
      (monitoring) => {
        if (monitoring) {
          console.log('🔄 開始自動更新儀表板數據');
        } else {
          console.log('⏸️ 暫停自動更新儀表板數據');
        }
      }
    );
  }

  /**
   * 刷新儀表板數據（不包含手動讀取電池數據）
   */
  private async refreshDashboardData(): Promise<void> {
    try {
      await Promise.all([
        this.loadActiveAlerts(),
        this.loadBatteryStats()
      ]);
    } catch (error) {
      console.error('❌ 刷新儀表板數據失敗:', error);
    }
  }

  /**
   * 重試上次操作
   */
  async retry(): Promise<void> {
    if (this.lastOperation) {
      await this.lastOperation();
    } else {
      await this.loadInitialData();
    }
  }

  /**
   * 清理資源
   */
  dispose(): void {
    super.dispose();
    
    if (this.updateTimer) {
      clearInterval(this.updateTimer);
      this.updateTimer = null;
    }
    
    console.log('🧹 儀表板 ViewModel 已清理');
  }

  // 計算屬性

  /**
   * 獲取電池電壓狀態
   */
  @computed
  get voltageStatus(): 'normal' | 'warning' | 'critical' {
    if (!this.batteryData) return 'normal';
    
    const voltage = this.batteryData.totalVoltage;
    if (voltage < 24.5 || voltage > 29.0) return 'critical';
    if (voltage < 25.0 || voltage > 28.5) return 'warning';
    return 'normal';
  }

  /**
   * 獲取電池溫度狀態
   */
  @computed
  get temperatureStatus(): 'normal' | 'warning' | 'critical' {
    if (!this.batteryData) return 'normal';
    
    const temp = this.batteryData.averageTemperature;
    if (temp > 55 || temp < -10) return 'critical';
    if (temp > 45 || temp < 0) return 'warning';
    return 'normal';
  }

  /**
   * 獲取電量狀態
   */
  @computed
  get socStatus(): 'normal' | 'warning' | 'critical' {
    if (!this.batteryData) return 'normal';
    
    const soc = this.batteryData.soc;
    if (soc < 10) return 'critical';
    if (soc < 20) return 'warning';
    return 'normal';
  }

  /**
   * 獲取連接狀態顯示文字
   */
  @computed
  get connectionStatusText(): string {
    switch (this.connectionStatus) {
      case ConnectionStatus.CONNECTED:
        return '已連接';
      case ConnectionStatus.CONNECTING:
        return '連接中';
      case ConnectionStatus.RECONNECTING:
        return '重新連接中';
      case ConnectionStatus.ERROR:
        return '連接錯誤';
      default:
        return '未連接';
    }
  }

  /**
   * 獲取是否有危險警報
   */
  @computed
  get hasCriticalAlerts(): boolean {
    return this.activeAlerts.some(alert => alert.severity === 'critical');
  }

  /**
   * 獲取最高優先級的警報
   */
  @computed
  get topAlert(): BatteryAlert | null {
    if (this.activeAlerts.length === 0) return null;
    
    // 優先級：critical > warning > info
    const critical = this.activeAlerts.find(alert => alert.severity === 'critical');
    if (critical) return critical;
    
    const warning = this.activeAlerts.find(alert => alert.severity === 'warning');
    if (warning) return warning;
    
    return this.activeAlerts[0];
  }

  /**
   * 獲取電池健康評分
   */
  @computed
  get healthScore(): number {
    return this.healthAssessment?.score || 0;
  }

  /**
   * 獲取電池健康狀態文字
   */
  @computed
  get healthStatusText(): string {
    const status = this.healthAssessment?.status;
    switch (status) {
      case 'excellent': return '優秀';
      case 'good': return '良好';
      case 'fair': return '一般';
      case 'poor': return '較差';
      case 'critical': return '危險';
      default: return '未知';
    }
  }
}