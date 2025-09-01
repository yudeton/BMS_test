import { injectable } from 'tsyringe';
import { IDataService } from '@services/interfaces/IDataService';
import { BatteryData, BatteryDataValidator, CurrentDirection, ConnectionStatus } from '@domain/entities/BatteryData';
import { BatteryAlert, AlertRule, AlertType, ComparisonOperator, AlertUtils } from '@domain/entities/AlertRule';

/**
 * 數據處理服務實作
 * 負責數據驗證、轉換、分析和警報檢查
 */
@injectable()
export class DataService implements IDataService {

  /**
   * 驗證電池數據的有效性
   */
  validateBatteryData(data: any): {
    isValid: boolean;
    errors: string[];
    sanitizedData?: BatteryData;
  } {
    try {
      // 使用領域實體的驗證器
      const validationResult = BatteryDataValidator.validate(data);
      
      if (!validationResult.isValid) {
        return {
          isValid: false,
          errors: validationResult.errors
        };
      }

      // 數據清理和標準化
      const sanitizedData = this.sanitizeData(data);
      
      return {
        isValid: true,
        errors: [],
        sanitizedData
      };

    } catch (error) {
      return {
        isValid: false,
        errors: [`數據驗證異常: ${error}`]
      };
    }
  }

  /**
   * 將原始 BMS 響應轉換為標準化數據格式
   */
  transformBMSData(rawData: any): BatteryData {
    const timestamp = new Date().toISOString();
    
    // 基本數據結構
    const batteryData: BatteryData = {
      timestamp,
      connectionStatus: ConnectionStatus.CONNECTED,
      totalVoltage: 0,
      current: 0,
      currentDirection: CurrentDirection.IDLE,
      power: 0,
      soc: 0,
      cells: [],
      temperatures: [],
      averageTemperature: 0,
      quality: {
        source: 'ble',
        crcValid: false,
        completenessScore: 0
      }
    };

    try {
      // 轉換總電壓
      if (rawData.extractedVoltage !== undefined || rawData.totalVoltage !== undefined) {
        batteryData.totalVoltage = rawData.extractedVoltage || rawData.totalVoltage;
      }

      // 轉換電流和方向
      if (rawData.extractedCurrent !== undefined || rawData.current !== undefined) {
        const current = rawData.extractedCurrent !== undefined ? rawData.extractedCurrent : rawData.current;
        batteryData.current = current;

        // 判斷電流方向
        if (current > 0.1) {
          batteryData.currentDirection = CurrentDirection.DISCHARGING;
        } else if (current < -0.1) {
          batteryData.currentDirection = CurrentDirection.CHARGING;
        } else {
          batteryData.currentDirection = CurrentDirection.IDLE;
        }
      }

      // 計算功率
      batteryData.power = batteryData.totalVoltage * batteryData.current;

      // 轉換電芯電壓
      if (rawData.extractedCellVoltages || rawData.cellVoltages) {
        batteryData.cells = rawData.extractedCellVoltages || rawData.cellVoltages;
      }

      // 轉換溫度
      if (rawData.extractedTemperatures || rawData.temperatures) {
        const temperatures = rawData.extractedTemperatures || rawData.temperatures;
        batteryData.temperatures = temperatures;
        batteryData.averageTemperature = temperatures.length > 0 
          ? temperatures.reduce((sum: number, temp: number) => sum + temp, 0) / temperatures.length
          : 0;
      }

      // 轉換 SOC
      if (rawData.soc !== undefined) {
        batteryData.soc = rawData.soc;
      } else if (batteryData.totalVoltage > 0) {
        // 基於電壓估算 SOC
        batteryData.soc = this.estimateSOCFromVoltage(batteryData.totalVoltage);
      }

      // 設置數據品質
      batteryData.quality = {
        source: 'ble',
        crcValid: rawData.crcValid || false,
        completenessScore: this.calculateCompletenessScore(batteryData)
      };

      console.log('🔄 BMS 數據轉換完成');
      return batteryData;

    } catch (error) {
      console.error('❌ BMS 數據轉換錯誤:', error);
      throw error;
    }
  }

  /**
   * 檢查警報條件
   */
  checkAlerts(data: BatteryData, rules: AlertRule[]): BatteryAlert[] {
    const alerts: BatteryAlert[] = [];
    const currentTime = new Date().toISOString();

    for (const rule of rules) {
      if (!rule.enabled) {
        continue;
      }

      try {
        const alert = this.evaluateAlertRule(data, rule, currentTime);
        if (alert) {
          alerts.push(alert);
        }
      } catch (error) {
        console.error(`❌ 評估警報規則錯誤 (${rule.id}):`, error);
      }
    }

    if (alerts.length > 0) {
      console.log(`🚨 觸發 ${alerts.length} 個警報`);
    }

    return alerts;
  }

  /**
   * 計算電池統計資訊
   */
  calculateBatteryStats(historicalData: BatteryData[]): {
    averageVoltage: number;
    maxVoltage: number;
    minVoltage: number;
    averageCurrent: number;
    averageTemperature: number;
    totalEnergyConsumed: number;
    cycleCount: number;
    healthScore: number;
  } {
    if (historicalData.length === 0) {
      return {
        averageVoltage: 0,
        maxVoltage: 0,
        minVoltage: 0,
        averageCurrent: 0,
        averageTemperature: 0,
        totalEnergyConsumed: 0,
        cycleCount: 0,
        healthScore: 0
      };
    }

    const voltages = historicalData.map(d => d.totalVoltage);
    const currents = historicalData.map(d => d.current);
    const temperatures = historicalData.map(d => d.averageTemperature);

    // 計算總能耗
    let totalEnergyConsumed = 0;
    for (let i = 1; i < historicalData.length; i++) {
      const current = historicalData[i];
      const previous = historicalData[i - 1];
      const timeDiff = (new Date(current.timestamp).getTime() - new Date(previous.timestamp).getTime()) / (1000 * 3600); // 小時
      
      if (timeDiff > 0 && timeDiff < 1) { // 限制在合理時間範圍內
        const avgPower = (current.power + previous.power) / 2;
        totalEnergyConsumed += Math.abs(avgPower * timeDiff); // Wh
      }
    }

    // 估算充放電循環次數
    const cycleCount = this.estimateCycleCount(historicalData);

    // 計算健康評分
    const healthScore = this.calculateHealthScore(historicalData);

    return {
      averageVoltage: this.average(voltages),
      maxVoltage: Math.max(...voltages),
      minVoltage: Math.min(...voltages),
      averageCurrent: this.average(currents),
      averageTemperature: this.average(temperatures),
      totalEnergyConsumed,
      cycleCount,
      healthScore
    };
  }

  /**
   * 估算剩餘使用時間
   */
  estimateRemainingTime(
    currentData: BatteryData,
    historicalData: BatteryData[]
  ): number | null {
    if (currentData.current <= 0 || currentData.soc <= 0) {
      return null; // 充電中或已耗盡
    }

    try {
      // 計算平均放電電流（過去一小時）
      const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
      const recentData = historicalData.filter(
        d => new Date(d.timestamp) > oneHourAgo && d.current > 0
      );

      const averageDischargeCurrent = recentData.length > 0
        ? this.average(recentData.map(d => d.current))
        : currentData.current;

      // 估算剩餘電量（假設 100Ah 電池）
      const batteryCapacity = 100; // Ah
      const remainingCapacity = (currentData.soc / 100) * batteryCapacity;

      // 計算剩餘時間（小時轉分鐘）
      const remainingTimeHours = remainingCapacity / averageDischargeCurrent;
      const remainingTimeMinutes = Math.round(remainingTimeHours * 60);

      console.log(`⏱️ 估算剩餘時間: ${remainingTimeMinutes} 分鐘`);
      return remainingTimeMinutes;

    } catch (error) {
      console.error('❌ 估算剩餘時間錯誤:', error);
      return null;
    }
  }

  /**
   * 檢測電池健康狀態
   */
  assessBatteryHealth(
    data: BatteryData,
    historicalData: BatteryData[]
  ): {
    score: number;
    status: 'excellent' | 'good' | 'fair' | 'poor' | 'critical';
    issues: string[];
    recommendations: string[];
  } {
    const issues: string[] = [];
    const recommendations: string[] = [];
    let score = 100;

    try {
      // 檢查電壓範圍
      if (data.totalVoltage < 24.5) {
        score -= 20;
        issues.push('總電壓偏低');
        recommendations.push('建議立即充電');
      } else if (data.totalVoltage > 29.0) {
        score -= 15;
        issues.push('總電壓偏高');
        recommendations.push('檢查充電器設定');
      }

      // 檢查電芯平衡
      if (data.cells.length > 0) {
        const maxCell = Math.max(...data.cells);
        const minCell = Math.min(...data.cells);
        const imbalance = maxCell - minCell;

        if (imbalance > 0.1) {
          score -= 25;
          issues.push('電芯不平衡嚴重');
          recommendations.push('進行電芯平衡處理');
        } else if (imbalance > 0.05) {
          score -= 10;
          issues.push('電芯輕微不平衡');
          recommendations.push('定期進行滿充平衡');
        }
      }

      // 檢查溫度
      if (data.averageTemperature > 45) {
        score -= 20;
        issues.push('溫度過高');
        recommendations.push('改善散熱環境');
      } else if (data.averageTemperature < 0) {
        score -= 15;
        issues.push('溫度過低');
        recommendations.push('注意低溫保護');
      }

      // 檢查歷史趨勢
      if (historicalData.length > 100) {
        const trends = this.analyzeTrends(historicalData);
        if (trends.voltageDecline) {
          score -= 15;
          issues.push('電壓衰減趨勢');
          recommendations.push('考慮專業檢測');
        }
      }

      // 確保分數在合理範圍內
      score = Math.max(0, Math.min(100, score));

      // 確定狀態等級
      let status: 'excellent' | 'good' | 'fair' | 'poor' | 'critical';
      if (score >= 90) status = 'excellent';
      else if (score >= 75) status = 'good';
      else if (score >= 60) status = 'fair';
      else if (score >= 40) status = 'poor';
      else status = 'critical';

      console.log(`💚 電池健康評估: ${status} (${score}分)`);

      return { score, status, issues, recommendations };

    } catch (error) {
      console.error('❌ 電池健康評估錯誤:', error);
      return {
        score: 0,
        status: 'critical',
        issues: ['健康評估失敗'],
        recommendations: ['請聯繫技術支援']
      };
    }
  }

  /**
   * 計算功率和能量
   */
  calculatePowerMetrics(
    voltage: number,
    current: number,
    previousData?: BatteryData
  ): {
    power: number;
    energyDelta?: number;
  } {
    const power = voltage * current;
    
    let energyDelta: number | undefined;
    
    if (previousData) {
      const timeDiff = Date.now() - new Date(previousData.timestamp).getTime();
      const timeDiffHours = timeDiff / (1000 * 60 * 60);
      
      if (timeDiffHours > 0 && timeDiffHours < 1) { // 限制在合理時間範圍內
        const avgPower = (power + previousData.power) / 2;
        energyDelta = avgPower * timeDiffHours; // Wh
      }
    }

    return { power, energyDelta };
  }

  /**
   * 平滑數據
   */
  smoothData<T extends { timestamp: string; [key: string]: any }>(
    data: T[],
    windowSize: number
  ): T[] {
    if (data.length < windowSize || windowSize < 2) {
      return data;
    }

    const smoothedData: T[] = [];
    
    for (let i = 0; i < data.length; i++) {
      const start = Math.max(0, i - Math.floor(windowSize / 2));
      const end = Math.min(data.length, start + windowSize);
      const window = data.slice(start, end);
      
      const smoothedItem = { ...data[i] };
      
      // 對數值欄位進行平滑處理
      const numericFields = ['totalVoltage', 'current', 'power', 'soc', 'averageTemperature'];
      
      for (const field of numericFields) {
        if (typeof data[i][field] === 'number') {
          const values = window.map(item => item[field]).filter(val => typeof val === 'number');
          if (values.length > 0) {
            smoothedItem[field] = this.average(values);
          }
        }
      }
      
      smoothedData.push(smoothedItem);
    }

    return smoothedData;
  }

  /**
   * 檢測數據異常
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
  } {
    const anomalies: Array<{
      field: string;
      currentValue: number;
      expectedRange: { min: number; max: number };
      severity: 'low' | 'medium' | 'high';
    }> = [];

    if (historicalData.length < 10) {
      return { hasAnomalies: false, anomalies };
    }

    try {
      // 檢查各個數值欄位
      const fieldsToCheck = [
        { field: 'totalVoltage', values: historicalData.map(d => d.totalVoltage) },
        { field: 'current', values: historicalData.map(d => d.current) },
        { field: 'averageTemperature', values: historicalData.map(d => d.averageTemperature) }
      ];

      for (const { field, values } of fieldsToCheck) {
        const mean = this.average(values);
        const stdDev = this.standardDeviation(values);
        
        const expectedRange = {
          min: mean - 2 * stdDev,
          max: mean + 2 * stdDev
        };

        const currentValue = (currentData as any)[field];
        
        if (typeof currentValue === 'number') {
          if (currentValue < expectedRange.min || currentValue > expectedRange.max) {
            const severity = this.getAnomalySeverity(currentValue, expectedRange, stdDev);
            anomalies.push({
              field,
              currentValue,
              expectedRange,
              severity
            });
          }
        }
      }

      const hasAnomalies = anomalies.length > 0;
      
      if (hasAnomalies) {
        console.log(`🔍 檢測到 ${anomalies.length} 個數據異常`);
      }

      return { hasAnomalies, anomalies };

    } catch (error) {
      console.error('❌ 異常檢測錯誤:', error);
      return { hasAnomalies: false, anomalies: [] };
    }
  }

  // 私有工具方法

  private sanitizeData(data: any): BatteryData {
    // 實現數據清理邏輯
    return {
      ...data,
      totalVoltage: this.clamp(data.totalVoltage || 0, 0, 100),
      current: this.clamp(data.current || 0, -200, 200),
      soc: this.clamp(data.soc || 0, 0, 100),
      cells: Array.isArray(data.cells) ? data.cells.filter((v: any) => typeof v === 'number') : [],
      temperatures: Array.isArray(data.temperatures) ? data.temperatures.filter((v: any) => typeof v === 'number') : []
    };
  }

  private estimateSOCFromVoltage(voltage: number): number {
    // 8S LiFePO4 電壓-SOC 估算
    const minVoltage = 24.0;
    const maxVoltage = 29.2;
    
    if (voltage <= minVoltage) return 0.0;
    if (voltage >= maxVoltage) return 100.0;
    
    const soc = ((voltage - minVoltage) / (maxVoltage - minVoltage)) * 100;
    return Math.round(soc * 10) / 10;
  }

  private calculateCompletenessScore(data: BatteryData): number {
    let score = 0;
    const totalFields = 8;

    if (data.totalVoltage > 0) score++;
    if (data.current !== undefined) score++;
    if (data.soc > 0) score++;
    if (data.cells.length > 0) score++;
    if (data.temperatures.length > 0) score++;
    if (data.averageTemperature !== undefined) score++;
    if (data.power !== undefined) score++;
    if (data.connectionStatus === ConnectionStatus.CONNECTED) score++;

    return Math.round((score / totalFields) * 100);
  }

  private evaluateAlertRule(data: BatteryData, rule: AlertRule, timestamp: string): BatteryAlert | null {
    let fieldValue: number;
    let cellNumber: number | undefined;

    // 獲取要檢查的欄位值
    switch (rule.field) {
      case 'totalVoltage':
        fieldValue = data.totalVoltage;
        break;
      case 'current':
        fieldValue = data.current;
        break;
      case 'soc':
        fieldValue = data.soc;
        break;
      case 'averageTemperature':
        fieldValue = data.averageTemperature;
        break;
      case 'cellVoltage':
        // 檢查所有電芯
        for (let i = 0; i < data.cells.length; i++) {
          const cellVoltage = data.cells[i];
          if (this.compareValue(cellVoltage, rule.operator, rule.threshold)) {
            return {
              ruleId: rule.id,
              type: rule.type,
              severity: rule.severity,
              message: AlertUtils.formatMessage(rule.messageTemplate, {
                value: cellVoltage.toFixed(3),
                threshold: rule.threshold,
                cell: i + 1
              }),
              value: cellVoltage,
              threshold: rule.threshold,
              cellNumber: i + 1,
              timestamp,
              acknowledged: false,
              resolved: false
            };
          }
        }
        return null;
      default:
        return null;
    }

    // 評估條件
    if (this.compareValue(fieldValue, rule.operator, rule.threshold)) {
      return {
        ruleId: rule.id,
        type: rule.type,
        severity: rule.severity,
        message: AlertUtils.formatMessage(rule.messageTemplate, {
          value: fieldValue,
          threshold: rule.threshold
        }),
        value: fieldValue,
        threshold: rule.threshold,
        cellNumber,
        timestamp,
        acknowledged: false,
        resolved: false
      };
    }

    return null;
  }

  private compareValue(value: number, operator: ComparisonOperator, threshold: number): boolean {
    switch (operator) {
      case ComparisonOperator.GREATER_THAN:
        return value > threshold;
      case ComparisonOperator.GREATER_THAN_OR_EQUAL:
        return value >= threshold;
      case ComparisonOperator.LESS_THAN:
        return value < threshold;
      case ComparisonOperator.LESS_THAN_OR_EQUAL:
        return value <= threshold;
      case ComparisonOperator.EQUAL:
        return Math.abs(value - threshold) < 0.001;
      case ComparisonOperator.NOT_EQUAL:
        return Math.abs(value - threshold) >= 0.001;
      default:
        return false;
    }
  }

  private estimateCycleCount(historicalData: BatteryData[]): number {
    // 簡化的循環計數估算
    let cycles = 0;
    let lastDirection = CurrentDirection.IDLE;
    
    for (const data of historicalData) {
      if (data.currentDirection !== lastDirection) {
        if ((lastDirection === CurrentDirection.CHARGING && data.currentDirection === CurrentDirection.DISCHARGING) ||
            (lastDirection === CurrentDirection.DISCHARGING && data.currentDirection === CurrentDirection.CHARGING)) {
          cycles += 0.5; // 半個循環
        }
        lastDirection = data.currentDirection;
      }
    }
    
    return Math.round(cycles);
  }

  private calculateHealthScore(historicalData: BatteryData[]): number {
    // 基於多個因素的健康評分算法
    if (historicalData.length < 10) return 100;
    
    let score = 100;
    
    // 檢查電壓衰減
    const recentVoltages = historicalData.slice(-50).map(d => d.totalVoltage);
    const olderVoltages = historicalData.slice(-100, -50).map(d => d.totalVoltage);
    
    if (recentVoltages.length > 0 && olderVoltages.length > 0) {
      const recentAvg = this.average(recentVoltages);
      const olderAvg = this.average(olderVoltages);
      
      if (recentAvg < olderAvg * 0.95) {
        score -= 20; // 電壓明顯衰減
      }
    }
    
    return Math.max(0, Math.min(100, score));
  }

  private analyzeTrends(historicalData: BatteryData[]): { voltageDecline: boolean } {
    if (historicalData.length < 50) {
      return { voltageDecline: false };
    }

    const voltages = historicalData.map(d => d.totalVoltage);
    const slope = this.calculateSlope(voltages);
    
    return {
      voltageDecline: slope < -0.001 // 明顯下降趨勢
    };
  }

  private calculateSlope(values: number[]): number {
    const n = values.length;
    const sumX = (n * (n - 1)) / 2;
    const sumY = values.reduce((sum, val) => sum + val, 0);
    const sumXY = values.reduce((sum, val, index) => sum + index * val, 0);
    const sumX2 = (n * (n - 1) * (2 * n - 1)) / 6;
    
    return (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  }

  private getAnomalySeverity(
    value: number, 
    expectedRange: { min: number; max: number }, 
    stdDev: number
  ): 'low' | 'medium' | 'high' {
    const deviation = Math.max(
      Math.abs(value - expectedRange.min),
      Math.abs(value - expectedRange.max)
    );
    
    if (deviation > 3 * stdDev) return 'high';
    if (deviation > 2.5 * stdDev) return 'medium';
    return 'low';
  }

  private average(values: number[]): number {
    return values.length > 0 ? values.reduce((sum, val) => sum + val, 0) / values.length : 0;
  }

  private standardDeviation(values: number[]): number {
    const mean = this.average(values);
    const squaredDiffs = values.map(val => Math.pow(val - mean, 2));
    return Math.sqrt(this.average(squaredDiffs));
  }

  private clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value));
  }
}