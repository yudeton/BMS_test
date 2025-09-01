import AsyncStorage from '@react-native-async-storage/async-storage';
import SQLite from 'react-native-sqlite-storage';
import { injectable } from 'tsyringe';
import { IStorageService, TimeRange, PaginationOptions } from '@services/interfaces/IStorageService';
import { BatteryData } from '@domain/entities/BatteryData';
import { BatteryAlert } from '@domain/entities/AlertRule';

/**
 * 資料庫配置
 */
const DB_CONFIG = {
  name: 'BMSMonitor.db',
  version: '1.0',
  displayName: 'BMS Monitor Database',
  size: 10 * 1024 * 1024 // 10MB
};

/**
 * AsyncStorage 配置鍵前綴
 */
const CONFIG_PREFIX = '@BMSMonitor:';

/**
 * 分層數據持久化服務實作
 * AsyncStorage（輕量配置） + SQLite（結構化數據）
 */
@injectable()
export class StorageService implements IStorageService {
  private db: SQLite.SQLiteDatabase | null = null;
  private initialized = false;

  constructor() {
    // 啟用 SQLite 調試（僅開發環境）
    if (__DEV__) {
      SQLite.DEBUG(true);
    }
    SQLite.enablePromise(true);
  }

  // ========== AsyncStorage 層（簡單配置） ==========

  /**
   * 保存配置資料
   */
  async saveConfig<T>(key: string, value: T): Promise<void> {
    try {
      const fullKey = CONFIG_PREFIX + key;
      const jsonValue = JSON.stringify(value);
      await AsyncStorage.setItem(fullKey, jsonValue);
      console.log(`💾 配置已保存: ${key}`);
    } catch (error) {
      console.error(`❌ 保存配置失敗 (${key}):`, error);
      throw error;
    }
  }

  /**
   * 讀取配置資料
   */
  async getConfig<T>(key: string): Promise<T | null> {
    try {
      const fullKey = CONFIG_PREFIX + key;
      const jsonValue = await AsyncStorage.getItem(fullKey);
      
      if (jsonValue === null) {
        return null;
      }

      return JSON.parse(jsonValue) as T;
    } catch (error) {
      console.error(`❌ 讀取配置失敗 (${key}):`, error);
      return null;
    }
  }

  /**
   * 刪除配置
   */
  async removeConfig(key: string): Promise<void> {
    try {
      const fullKey = CONFIG_PREFIX + key;
      await AsyncStorage.removeItem(fullKey);
      console.log(`🗑️ 配置已刪除: ${key}`);
    } catch (error) {
      console.error(`❌ 刪除配置失敗 (${key}):`, error);
      throw error;
    }
  }

  /**
   * 清空所有配置
   */
  async clearAllConfig(): Promise<void> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      const configKeys = keys.filter(key => key.startsWith(CONFIG_PREFIX));
      
      if (configKeys.length > 0) {
        await AsyncStorage.multiRemove(configKeys);
        console.log(`🧹 已清空 ${configKeys.length} 個配置項目`);
      }
    } catch (error) {
      console.error('❌ 清空配置失敗:', error);
      throw error;
    }
  }

  // ========== SQLite 層（結構化數據） ==========

  /**
   * 初始化數據庫
   */
  async initializeDatabase(): Promise<void> {
    if (this.initialized) {
      return;
    }

    try {
      console.log('🗃️ 初始化 SQLite 數據庫...');

      // 打開數據庫
      this.db = await SQLite.openDatabase({
        name: DB_CONFIG.name,
        version: DB_CONFIG.version,
        displayName: DB_CONFIG.displayName,
        size: DB_CONFIG.size,
        location: 'default'
      });

      // 創建表格
      await this.createTables();

      this.initialized = true;
      console.log('✅ 數據庫初始化完成');

    } catch (error) {
      console.error('❌ 數據庫初始化失敗:', error);
      throw error;
    }
  }

  /**
   * 創建數據庫表格
   */
  private async createTables(): Promise<void> {
    if (!this.db) {
      throw new Error('數據庫未初始化');
    }

    const tables = [
      // 電池數據表
      `CREATE TABLE IF NOT EXISTS battery_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        connection_status TEXT NOT NULL,
        total_voltage REAL NOT NULL,
        current REAL NOT NULL,
        current_direction TEXT NOT NULL,
        power REAL NOT NULL,
        soc REAL NOT NULL,
        cells TEXT, -- JSON 陣列
        temperatures TEXT, -- JSON 陣列
        average_temperature REAL,
        mosfet_status TEXT, -- JSON 物件
        fault_status TEXT, -- JSON 物件
        quality TEXT NOT NULL, -- JSON 物件
        stats TEXT, -- JSON 物件
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
      )`,

      // 警報記錄表
      `CREATE TABLE IF NOT EXISTS battery_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_id TEXT NOT NULL,
        type TEXT NOT NULL,
        severity TEXT NOT NULL,
        message TEXT NOT NULL,
        value REAL NOT NULL,
        threshold REAL NOT NULL,
        cell_number INTEGER,
        timestamp TEXT NOT NULL,
        acknowledged INTEGER NOT NULL DEFAULT 0,
        acknowledged_at TEXT,
        resolved INTEGER NOT NULL DEFAULT 0,
        resolved_at TEXT,
        notification_id TEXT,
        metadata TEXT, -- JSON 物件
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
      )`,

      // 索引
      `CREATE INDEX IF NOT EXISTS idx_battery_data_timestamp ON battery_data(timestamp)`,
      `CREATE INDEX IF NOT EXISTS idx_battery_alerts_timestamp ON battery_alerts(timestamp)`,
      `CREATE INDEX IF NOT EXISTS idx_battery_alerts_severity ON battery_alerts(severity)`,
      `CREATE INDEX IF NOT EXISTS idx_battery_alerts_acknowledged ON battery_alerts(acknowledged)`
    ];

    for (const sql of tables) {
      await this.db.executeSql(sql);
    }

    console.log('📋 數據庫表格創建完成');
  }

  /**
   * 保存電池數據
   */
  async saveBatteryData(data: BatteryData): Promise<number> {
    if (!this.db) {
      await this.initializeDatabase();
    }

    try {
      const sql = `
        INSERT INTO battery_data (
          timestamp, connection_status, total_voltage, current, current_direction,
          power, soc, cells, temperatures, average_temperature,
          mosfet_status, fault_status, quality, stats
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `;

      const params = [
        data.timestamp,
        data.connectionStatus,
        data.totalVoltage,
        data.current,
        data.currentDirection,
        data.power,
        data.soc,
        JSON.stringify(data.cells),
        JSON.stringify(data.temperatures),
        data.averageTemperature,
        data.mosfetStatus ? JSON.stringify(data.mosfetStatus) : null,
        data.faultStatus ? JSON.stringify(data.faultStatus) : null,
        JSON.stringify(data.quality),
        data.stats ? JSON.stringify(data.stats) : null
      ];

      const result = await this.db!.executeSql(sql, params);
      const insertId = result[0].insertId;

      console.log(`💾 電池數據已保存: ID ${insertId}`);
      return insertId;

    } catch (error) {
      console.error('❌ 保存電池數據失敗:', error);
      throw error;
    }
  }

  /**
   * 查詢電池歷史數據
   */
  async getBatteryHistory(
    timeRange?: TimeRange,
    pagination?: PaginationOptions
  ): Promise<BatteryData[]> {
    if (!this.db) {
      await this.initializeDatabase();
    }

    try {
      let sql = 'SELECT * FROM battery_data';
      const params: any[] = [];

      // 添加時間範圍條件
      if (timeRange) {
        sql += ' WHERE timestamp >= ? AND timestamp <= ?';
        params.push(timeRange.startTime.toISOString(), timeRange.endTime.toISOString());
      }

      // 排序
      sql += ' ORDER BY timestamp DESC';

      // 添加分頁
      if (pagination) {
        sql += ' LIMIT ? OFFSET ?';
        params.push(pagination.limit, pagination.offset);
      }

      const result = await this.db!.executeSql(sql, params);
      const rows = result[0].rows;
      const data: BatteryData[] = [];

      for (let i = 0; i < rows.length; i++) {
        const row = rows.item(i);
        data.push(this.rowToBatteryData(row));
      }

      console.log(`📊 查詢到 ${data.length} 筆電池數據`);
      return data;

    } catch (error) {
      console.error('❌ 查詢電池歷史數據失敗:', error);
      throw error;
    }
  }

  /**
   * 獲取最新的電池數據
   */
  async getLatestBatteryData(): Promise<BatteryData | null> {
    if (!this.db) {
      await this.initializeDatabase();
    }

    try {
      const sql = 'SELECT * FROM battery_data ORDER BY timestamp DESC LIMIT 1';
      const result = await this.db!.executeSql(sql);

      if (result[0].rows.length === 0) {
        return null;
      }

      const row = result[0].rows.item(0);
      return this.rowToBatteryData(row);

    } catch (error) {
      console.error('❌ 獲取最新電池數據失敗:', error);
      return null;
    }
  }

  /**
   * 保存警報記錄
   */
  async saveAlert(alert: BatteryAlert): Promise<number> {
    if (!this.db) {
      await this.initializeDatabase();
    }

    try {
      const sql = `
        INSERT INTO battery_alerts (
          rule_id, type, severity, message, value, threshold, cell_number,
          timestamp, acknowledged, acknowledged_at, resolved, resolved_at,
          notification_id, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `;

      const params = [
        alert.ruleId,
        alert.type,
        alert.severity,
        alert.message,
        alert.value,
        alert.threshold,
        alert.cellNumber || null,
        alert.timestamp,
        alert.acknowledged ? 1 : 0,
        alert.acknowledgedAt || null,
        alert.resolved ? 1 : 0,
        alert.resolvedAt || null,
        alert.notificationId || null,
        alert.metadata ? JSON.stringify(alert.metadata) : null
      ];

      const result = await this.db!.executeSql(sql, params);
      const insertId = result[0].insertId;

      console.log(`🚨 警報記錄已保存: ID ${insertId}`);
      return insertId;

    } catch (error) {
      console.error('❌ 保存警報記錄失敗:', error);
      throw error;
    }
  }

  /**
   * 查詢警報歷史
   */
  async getAlertHistory(
    timeRange?: TimeRange,
    pagination?: PaginationOptions
  ): Promise<BatteryAlert[]> {
    if (!this.db) {
      await this.initializeDatabase();
    }

    try {
      let sql = 'SELECT * FROM battery_alerts';
      const params: any[] = [];

      // 添加時間範圍條件
      if (timeRange) {
        sql += ' WHERE timestamp >= ? AND timestamp <= ?';
        params.push(timeRange.startTime.toISOString(), timeRange.endTime.toISOString());
      }

      // 排序
      sql += ' ORDER BY timestamp DESC';

      // 添加分頁
      if (pagination) {
        sql += ' LIMIT ? OFFSET ?';
        params.push(pagination.limit, pagination.offset);
      }

      const result = await this.db!.executeSql(sql, params);
      const rows = result[0].rows;
      const alerts: BatteryAlert[] = [];

      for (let i = 0; i < rows.length; i++) {
        const row = rows.item(i);
        alerts.push(this.rowToBatteryAlert(row));
      }

      console.log(`🚨 查詢到 ${alerts.length} 筆警報記錄`);
      return alerts;

    } catch (error) {
      console.error('❌ 查詢警報歷史失敗:', error);
      throw error;
    }
  }

  /**
   * 清理舊數據
   */
  async cleanupOldData(olderThanDays: number): Promise<void> {
    if (!this.db) {
      await this.initializeDatabase();
    }

    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - olderThanDays);
      const cutoffTimestamp = cutoffDate.toISOString();

      // 清理舊的電池數據
      const batteryDataSql = 'DELETE FROM battery_data WHERE timestamp < ?';
      const batteryResult = await this.db!.executeSql(batteryDataSql, [cutoffTimestamp]);
      const batteryDeleted = batteryResult[0].rowsAffected;

      // 清理舊的警報記錄
      const alertsSql = 'DELETE FROM battery_alerts WHERE timestamp < ?';
      const alertsResult = await this.db!.executeSql(alertsSql, [cutoffTimestamp]);
      const alertsDeleted = alertsResult[0].rowsAffected;

      console.log(`🧹 數據清理完成: 電池數據 ${batteryDeleted} 筆, 警報記錄 ${alertsDeleted} 筆`);

    } catch (error) {
      console.error('❌ 清理舊數據失敗:', error);
      throw error;
    }
  }

  /**
   * 獲取存儲統計資訊
   */
  async getStorageStats(): Promise<{
    batteryDataCount: number;
    alertCount: number;
    databaseSize: number;
    oldestRecord: Date | null;
    newestRecord: Date | null;
  }> {
    if (!this.db) {
      await this.initializeDatabase();
    }

    try {
      // 獲取電池數據統計
      const batteryCountResult = await this.db!.executeSql('SELECT COUNT(*) as count FROM battery_data');
      const batteryDataCount = batteryCountResult[0].rows.item(0).count;

      // 獲取警報統計
      const alertCountResult = await this.db!.executeSql('SELECT COUNT(*) as count FROM battery_alerts');
      const alertCount = alertCountResult[0].rows.item(0).count;

      // 獲取時間範圍
      const timeRangeResult = await this.db!.executeSql(`
        SELECT 
          MIN(timestamp) as oldest,
          MAX(timestamp) as newest
        FROM battery_data
      `);
      
      const timeRange = timeRangeResult[0].rows.item(0);
      const oldestRecord = timeRange.oldest ? new Date(timeRange.oldest) : null;
      const newestRecord = timeRange.newest ? new Date(timeRange.newest) : null;

      // 獲取數據庫大小（估算）
      const databaseSize = 0; // SQLite 沒有直接獲取大小的方法

      const stats = {
        batteryDataCount,
        alertCount,
        databaseSize,
        oldestRecord,
        newestRecord
      };

      console.log('📊 存儲統計:', stats);
      return stats;

    } catch (error) {
      console.error('❌ 獲取存儲統計失敗:', error);
      throw error;
    }
  }

  /**
   * 匯出數據
   */
  async exportData(timeRange?: TimeRange): Promise<string> {
    try {
      const batteryData = await this.getBatteryHistory(timeRange);
      const alertData = await this.getAlertHistory(timeRange);

      const exportData = {
        exportTime: new Date().toISOString(),
        timeRange,
        summary: {
          batteryDataCount: batteryData.length,
          alertCount: alertData.length
        },
        batteryData,
        alerts: alertData
      };

      const jsonString = JSON.stringify(exportData, null, 2);
      console.log(`📤 數據匯出完成: ${batteryData.length} 筆電池數據, ${alertData.length} 筆警報`);
      
      return jsonString;

    } catch (error) {
      console.error('❌ 匯出數據失敗:', error);
      throw error;
    }
  }

  /**
   * 關閉數據庫連接
   */
  async closeDatabase(): Promise<void> {
    if (this.db) {
      try {
        await this.db.close();
        this.db = null;
        this.initialized = false;
        console.log('🔒 數據庫連接已關閉');
      } catch (error) {
        console.error('❌ 關閉數據庫失敗:', error);
        throw error;
      }
    }
  }

  /**
   * 服務關閉
   */
  async shutdown(): Promise<void> {
    await this.closeDatabase();
  }

  // 私有工具方法

  private rowToBatteryData(row: any): BatteryData {
    return {
      id: row.id,
      timestamp: row.timestamp,
      connectionStatus: row.connection_status,
      totalVoltage: row.total_voltage,
      current: row.current,
      currentDirection: row.current_direction,
      power: row.power,
      soc: row.soc,
      cells: row.cells ? JSON.parse(row.cells) : [],
      temperatures: row.temperatures ? JSON.parse(row.temperatures) : [],
      averageTemperature: row.average_temperature,
      mosfetStatus: row.mosfet_status ? JSON.parse(row.mosfet_status) : undefined,
      faultStatus: row.fault_status ? JSON.parse(row.fault_status) : undefined,
      quality: JSON.parse(row.quality),
      stats: row.stats ? JSON.parse(row.stats) : undefined
    };
  }

  private rowToBatteryAlert(row: any): BatteryAlert {
    return {
      id: row.id,
      ruleId: row.rule_id,
      type: row.type,
      severity: row.severity,
      message: row.message,
      value: row.value,
      threshold: row.threshold,
      cellNumber: row.cell_number,
      timestamp: row.timestamp,
      acknowledged: Boolean(row.acknowledged),
      acknowledgedAt: row.acknowledged_at,
      resolved: Boolean(row.resolved),
      resolvedAt: row.resolved_at,
      notificationId: row.notification_id,
      metadata: row.metadata ? JSON.parse(row.metadata) : undefined
    };
  }
}