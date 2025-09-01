/**
 * 警報嚴重程度枚舉
 */
export enum AlertSeverity {
  INFO = 'info',
  WARNING = 'warning', 
  CRITICAL = 'critical'
}

/**
 * 警報類型枚舉
 */
export enum AlertType {
  VOLTAGE_HIGH = 'voltage_high',
  VOLTAGE_LOW = 'voltage_low',
  CURRENT_HIGH = 'current_high',
  TEMPERATURE_HIGH = 'temperature_high',
  TEMPERATURE_LOW = 'temperature_low',
  SOC_LOW = 'soc_low',
  CELL_VOLTAGE_IMBALANCE = 'cell_voltage_imbalance',
  CONNECTION_LOST = 'connection_lost',
  DATA_QUALITY_LOW = 'data_quality_low',
  CHARGING_FAULT = 'charging_fault',
  DISCHARGING_FAULT = 'discharging_fault'
}

/**
 * 比較運算子枚舉
 */
export enum ComparisonOperator {
  GREATER_THAN = '>',
  LESS_THAN = '<',
  GREATER_THAN_OR_EQUAL = '>=',
  LESS_THAN_OR_EQUAL = '<=',
  EQUAL = '=',
  NOT_EQUAL = '!='
}

/**
 * 警報規則實體
 * 定義觸發警報的條件
 */
export interface AlertRule {
  /** 規則 ID */
  id: string;

  /** 規則名稱 */
  name: string;

  /** 警報類型 */
  type: AlertType;

  /** 嚴重程度 */
  severity: AlertSeverity;

  /** 是否啟用此規則 */
  enabled: boolean;

  /** 監控的資料欄位 */
  field: string;

  /** 比較運算子 */
  operator: ComparisonOperator;

  /** 閾值 */
  threshold: number;

  /** 可選：第二個閾值（用於範圍檢查） */
  secondaryThreshold?: number;

  /** 觸發條件持續時間（秒）*/
  durationSeconds?: number;

  /** 冷卻期間（秒）- 避免重複警報 */
  cooldownSeconds: number;

  /** 警報訊息模板 */
  messageTemplate: string;

  /** 是否發送通知 */
  sendNotification: boolean;

  /** 自訂屬性 */
  customProperties?: Record<string, any>;

  /** 創建時間 */
  createdAt: string;

  /** 最後修改時間 */
  updatedAt: string;
}

/**
 * 警報實體
 * 實際觸發的警報記錄
 */
export interface BatteryAlert {
  /** 警報 ID */
  id?: number;

  /** 對應的規則 ID */
  ruleId: string;

  /** 警報類型 */
  type: AlertType;

  /** 嚴重程度 */
  severity: AlertSeverity;

  /** 警報訊息 */
  message: string;

  /** 觸發時的數值 */
  value: number;

  /** 觸發閾值 */
  threshold: number;

  /** 相關的電芯編號（如果適用） */
  cellNumber?: number;

  /** 觸發時間 */
  timestamp: string;

  /** 是否已確認 */
  acknowledged: boolean;

  /** 確認時間 */
  acknowledgedAt?: string;

  /** 是否已解決 */
  resolved: boolean;

  /** 解決時間 */
  resolvedAt?: string;

  /** 通知 ID（用於取消通知） */
  notificationId?: string;

  /** 額外的上下文資料 */
  metadata?: Record<string, any>;
}

/**
 * 預設警報規則集
 */
export const DEFAULT_ALERT_RULES: AlertRule[] = [
  {
    id: 'voltage-high-critical',
    name: '總電壓過高（危險）',
    type: AlertType.VOLTAGE_HIGH,
    severity: AlertSeverity.CRITICAL,
    enabled: true,
    field: 'totalVoltage',
    operator: ComparisonOperator.GREATER_THAN,
    threshold: 30.4, // 8S LiFePO4 最大安全電壓
    cooldownSeconds: 60,
    messageTemplate: '⚠️ 總電壓過高: {{value}}V (閾值: {{threshold}}V)',
    sendNotification: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: 'voltage-low-critical', 
    name: '總電壓過低（危險）',
    type: AlertType.VOLTAGE_LOW,
    severity: AlertSeverity.CRITICAL,
    enabled: true,
    field: 'totalVoltage',
    operator: ComparisonOperator.LESS_THAN,
    threshold: 24.0, // 8S LiFePO4 最低安全電壓
    cooldownSeconds: 60,
    messageTemplate: '🔋 總電壓過低: {{value}}V (閾值: {{threshold}}V)',
    sendNotification: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: 'temperature-high-warning',
    name: '溫度過高（警告）',
    type: AlertType.TEMPERATURE_HIGH,
    severity: AlertSeverity.WARNING,
    enabled: true,
    field: 'averageTemperature',
    operator: ComparisonOperator.GREATER_THAN,
    threshold: 45.0,
    cooldownSeconds: 300,
    messageTemplate: '🌡️ 溫度過高: {{value}}°C (閾值: {{threshold}}°C)',
    sendNotification: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: 'temperature-high-critical',
    name: '溫度過高（危險）',
    type: AlertType.TEMPERATURE_HIGH,
    severity: AlertSeverity.CRITICAL,
    enabled: true,
    field: 'averageTemperature', 
    operator: ComparisonOperator.GREATER_THAN,
    threshold: 55.0,
    cooldownSeconds: 60,
    messageTemplate: '🔥 溫度危險: {{value}}°C (閾值: {{threshold}}°C)',
    sendNotification: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: 'soc-low-warning',
    name: '電量不足（警告）',
    type: AlertType.SOC_LOW,
    severity: AlertSeverity.WARNING,
    enabled: true,
    field: 'soc',
    operator: ComparisonOperator.LESS_THAN,
    threshold: 20.0,
    cooldownSeconds: 1800, // 30 分鐘冷卻
    messageTemplate: '🔋 電量不足: {{value}}% (閾值: {{threshold}}%)',
    sendNotification: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: 'soc-low-critical',
    name: '電量極低（危險）',
    type: AlertType.SOC_LOW,
    severity: AlertSeverity.CRITICAL,
    enabled: true,
    field: 'soc',
    operator: ComparisonOperator.LESS_THAN,
    threshold: 10.0,
    cooldownSeconds: 300, // 5 分鐘冷卻
    messageTemplate: '⚠️ 電量極低: {{value}}% (閾值: {{threshold}}%)',
    sendNotification: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: 'connection-lost',
    name: '連接中斷',
    type: AlertType.CONNECTION_LOST,
    severity: AlertSeverity.WARNING,
    enabled: true,
    field: 'connectionStatus',
    operator: ComparisonOperator.EQUAL,
    threshold: 0, // 假設 0 表示斷線
    cooldownSeconds: 120,
    messageTemplate: '📡 BMS 連接中斷',
    sendNotification: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  }
];

/**
 * 警報工具類
 */
export class AlertUtils {
  /**
   * 插值替換警報訊息模板
   * @param template 訊息模板
   * @param values 替換值
   * @returns 格式化後的訊息
   */
  static formatMessage(template: string, values: Record<string, any>): string {
    return template.replace(/\{\{(\w+)\}\}/g, (match, key) => {
      return values[key]?.toString() || match;
    });
  }

  /**
   * 檢查警報是否在冷卻期
   * @param alert 上次觸發的警報
   * @param rule 警報規則
   * @returns 是否在冷卻期
   */
  static isInCooldown(alert: BatteryAlert, rule: AlertRule): boolean {
    const lastTriggered = new Date(alert.timestamp).getTime();
    const now = Date.now();
    const cooldownMs = rule.cooldownSeconds * 1000;
    
    return (now - lastTriggered) < cooldownMs;
  }

  /**
   * 根據嚴重程度獲取顏色
   * @param severity 嚴重程度
   * @returns 顏色代碼
   */
  static getSeverityColor(severity: AlertSeverity): string {
    switch (severity) {
      case AlertSeverity.INFO:
        return '#2196F3'; // 藍色
      case AlertSeverity.WARNING:
        return '#FF9800'; // 橙色  
      case AlertSeverity.CRITICAL:
        return '#F44336'; // 紅色
      default:
        return '#757575'; // 灰色
    }
  }

  /**
   * 根據嚴重程度獲取圖標
   * @param severity 嚴重程度
   * @returns 圖標名稱
   */
  static getSeverityIcon(severity: AlertSeverity): string {
    switch (severity) {
      case AlertSeverity.INFO:
        return 'info';
      case AlertSeverity.WARNING:
        return 'warning';
      case AlertSeverity.CRITICAL:
        return 'error';
      default:
        return 'help';
    }
  }
}