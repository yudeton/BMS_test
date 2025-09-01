import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text, DataText, Label } from '../common/Text';
import { Card } from '../common/Card';
import { useThemeOnly } from '../../theme/ThemeProvider';
import { getSOCColor, getBatteryStatusColor } from '../../theme/colors';
import { BatteryData, ConnectionStatus } from '../../../domain/entities/BatteryData';

/**
 * 電池狀態卡片組件屬性
 */
interface BatteryStatusCardProps {
  batteryData: BatteryData | null;
  connectionStatus: ConnectionStatus;
  onPress?: () => void;
}

/**
 * 電池狀態卡片組件
 * 顯示電池的主要狀態資訊
 */
export const BatteryStatusCard: React.FC<BatteryStatusCardProps> = ({
  batteryData,
  connectionStatus,
  onPress,
}) => {
  const theme = useThemeOnly();

  /**
   * 獲取連接狀態文字和顏色
   */
  const getConnectionInfo = () => {
    switch (connectionStatus) {
      case ConnectionStatus.CONNECTED:
        return { text: '已連接', color: theme.colors.success };
      case ConnectionStatus.CONNECTING:
        return { text: '連接中', color: theme.colors.warning };
      case ConnectionStatus.RECONNECTING:
        return { text: '重新連接中', color: theme.colors.warning };
      case ConnectionStatus.ERROR:
        return { text: '連接錯誤', color: theme.colors.error };
      default:
        return { text: '未連接', color: theme.colors.textSecondary };
    }
  };

  /**
   * 獲取電池健康狀態
   */
  const getBatteryHealthStatus = () => {
    if (!batteryData) return { status: 'unknown', color: theme.colors.textSecondary };

    const voltage = batteryData.totalVoltage;
    const temp = batteryData.averageTemperature;
    const soc = batteryData.soc;

    // 危險狀態檢查
    if (voltage < 24.0 || voltage > 30.4 || temp > 55 || soc < 5) {
      return { status: 'critical', color: theme.colors.error };
    }

    // 警告狀態檢查
    if (voltage < 25.0 || voltage > 29.0 || temp > 45 || soc < 15) {
      return { status: 'warning', color: theme.colors.warning };
    }

    return { status: 'normal', color: theme.colors.success };
  };

  /**
   * 格式化時間顯示
   */
  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-TW', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const connectionInfo = getConnectionInfo();
  const healthStatus = getBatteryHealthStatus();

  return (
    <Card onPress={onPress} elevation="md">
      {/* 卡片標題 */}
      <View style={styles.header}>
        <Text variant="h4">電池狀態</Text>
        <View style={[styles.statusIndicator, { backgroundColor: connectionInfo.color }]} />
      </View>

      {/* 連接狀態 */}
      <View style={styles.connectionStatus}>
        <Label>連接狀態</Label>
        <Text variant="body2" color={connectionInfo.color}>
          {connectionInfo.text}
        </Text>
      </View>

      {batteryData ? (
        <>
          {/* 主要數據網格 */}
          <View style={styles.dataGrid}>
            {/* 電壓 */}
            <View style={styles.dataItem}>
              <Label>總電壓</Label>
              <View style={styles.dataRow}>
                <DataText 
                  size="large" 
                  unit="V"
                  color={getBatteryStatusColor(
                    batteryData.totalVoltage < 24.5 ? 'critical' : 
                    batteryData.totalVoltage > 29.0 ? 'warning' : 'normal',
                    theme
                  )}
                >
                  {batteryData.totalVoltage.toFixed(1)}
                </DataText>
              </View>
            </View>

            {/* 電流 */}
            <View style={styles.dataItem}>
              <Label>電流</Label>
              <View style={styles.dataRow}>
                <DataText 
                  size="large" 
                  unit="A"
                  color={
                    batteryData.current > 0.1 ? theme.colors.warning :
                    batteryData.current < -0.1 ? theme.colors.info : 
                    theme.colors.textSecondary
                  }
                >
                  {batteryData.current.toFixed(1)}
                </DataText>
              </View>
              <Text 
                variant="caption" 
                color={theme.colors.textSecondary}
                style={{ textAlign: 'center', marginTop: 2 }}
              >
                {batteryData.currentDirection === 'charging' ? '充電中' :
                 batteryData.currentDirection === 'discharging' ? '放電中' : '靜止'}
              </Text>
            </View>
          </View>

          {/* 電量和溫度 */}
          <View style={styles.secondaryData}>
            {/* SOC */}
            <View style={styles.compactDataItem}>
              <Label>電量</Label>
              <View style={styles.dataRow}>
                <DataText 
                  size="medium" 
                  unit="%"
                  color={getSOCColor(batteryData.soc, theme)}
                >
                  {batteryData.soc.toFixed(0)}
                </DataText>
              </View>
            </View>

            {/* 功率 */}
            <View style={styles.compactDataItem}>
              <Label>功率</Label>
              <View style={styles.dataRow}>
                <DataText 
                  size="medium" 
                  unit="W"
                  color={theme.colors.text}
                >
                  {Math.abs(batteryData.power).toFixed(0)}
                </DataText>
              </View>
            </View>

            {/* 溫度 */}
            <View style={styles.compactDataItem}>
              <Label>溫度</Label>
              <View style={styles.dataRow}>
                <DataText 
                  size="medium" 
                  unit="°C"
                  color={
                    batteryData.averageTemperature > 50 ? theme.colors.error :
                    batteryData.averageTemperature > 40 ? theme.colors.warning :
                    theme.colors.text
                  }
                >
                  {batteryData.averageTemperature.toFixed(0)}
                </DataText>
              </View>
            </View>
          </View>

          {/* 底部資訊 */}
          <View style={styles.footer}>
            <View style={styles.healthStatus}>
              <View style={[styles.healthIndicator, { backgroundColor: healthStatus.color }]} />
              <Text variant="caption" color={healthStatus.color}>
                {healthStatus.status === 'critical' ? '危險' :
                 healthStatus.status === 'warning' ? '警告' :
                 healthStatus.status === 'normal' ? '正常' : '未知'}
              </Text>
            </View>
            
            <Text variant="caption" color={theme.colors.textSecondary}>
              更新時間: {formatTime(batteryData.timestamp)}
            </Text>
          </View>
        </>
      ) : (
        /* 無數據狀態 */
        <View style={styles.noDataContainer}>
          <Text variant="h2" style={{ textAlign: 'center', marginBottom: 8 }}>
            📊
          </Text>
          <Text 
            variant="body2" 
            color={theme.colors.textSecondary}
            style={{ textAlign: 'center' }}
          >
            {connectionStatus === ConnectionStatus.CONNECTED ? 
              '正在讀取電池數據...' : 
              '請先連接 BMS 設備'
            }
          </Text>
        </View>
      )}
    </Card>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  statusIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  connectionStatus: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  dataGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  dataItem: {
    flex: 1,
    alignItems: 'center',
  },
  dataRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'center',
    marginTop: 4,
  },
  secondaryData: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 16,
    paddingVertical: 12,
    backgroundColor: 'rgba(0,0,0,0.02)',
    borderRadius: 8,
  },
  compactDataItem: {
    alignItems: 'center',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F0F0F0',
  },
  healthStatus: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  healthIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  noDataContainer: {
    alignItems: 'center',
    paddingVertical: 40,
  },
});