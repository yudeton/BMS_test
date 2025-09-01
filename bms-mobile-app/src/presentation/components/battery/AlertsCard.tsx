import React from 'react';
import { View, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { Text, Label, Caption } from '../common/Text';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { useThemeOnly } from '../../theme/ThemeProvider';
import { BatteryAlert, AlertSeverity, AlertUtils } from '../../../domain/entities/AlertRule';

/**
 * 警報卡片組件屬性
 */
interface AlertsCardProps {
  alerts: BatteryAlert[];
  onViewAllAlerts?: () => void;
  onAcknowledgeAlert?: (alertId: number) => void;
  onAlertPress?: (alert: BatteryAlert) => void;
}

/**
 * 警報卡片組件
 * 顯示活躍警報和警報摘要
 */
export const AlertsCard: React.FC<AlertsCardProps> = ({
  alerts,
  onViewAllAlerts,
  onAcknowledgeAlert,
  onAlertPress,
}) => {
  const theme = useThemeOnly();

  /**
   * 獲取警報嚴重程度圖標
   */
  const getAlertIcon = (severity: AlertSeverity): string => {
    switch (severity) {
      case AlertSeverity.CRITICAL:
        return '🚨';
      case AlertSeverity.WARNING:
        return '⚠️';
      case AlertSeverity.INFO:
        return 'ℹ️';
      default:
        return '📋';
    }
  };

  /**
   * 獲取警報嚴重程度文字
   */
  const getSeverityText = (severity: AlertSeverity): string => {
    switch (severity) {
      case AlertSeverity.CRITICAL:
        return '危險';
      case AlertSeverity.WARNING:
        return '警告';
      case AlertSeverity.INFO:
        return '資訊';
      default:
        return '未知';
    }
  };

  /**
   * 格式化時間顯示
   */
  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    if (diff < 60000) { // 1分鐘內
      return '剛剛';
    } else if (diff < 3600000) { // 1小時內
      return `${Math.floor(diff / 60000)} 分鐘前`;
    } else if (diff < 86400000) { // 24小時內
      return `${Math.floor(diff / 3600000)} 小時前`;
    } else {
      return date.toLocaleDateString('zh-TW');
    }
  };

  /**
   * 計算警報統計
   */
  const getAlertStats = () => {
    const critical = alerts.filter(a => a.severity === AlertSeverity.CRITICAL).length;
    const warning = alerts.filter(a => a.severity === AlertSeverity.WARNING).length;
    const info = alerts.filter(a => a.severity === AlertSeverity.INFO).length;
    
    return { critical, warning, info, total: alerts.length };
  };

  /**
   * 渲染單個警報項目
   */
  const renderAlertItem = (alert: BatteryAlert, index: number): JSX.Element => {
    const severityColor = AlertUtils.getSeverityColor(alert.severity);
    
    return (
      <TouchableOpacity
        key={alert.id || index}
        style={[styles.alertItem, { borderLeftColor: severityColor }]}
        onPress={() => onAlertPress?.(alert)}
        activeOpacity={0.7}
      >
        <View style={styles.alertHeader}>
          <View style={styles.alertTitleRow}>
            <Text variant="body2" style={{ marginRight: 8 }}>
              {getAlertIcon(alert.severity)}
            </Text>
            <View style={styles.alertContent}>
              <Text 
                variant="body2" 
                color={severityColor}
                numberOfLines={2}
              >
                {alert.message}
              </Text>
              <Caption color={theme.colors.textSecondary}>
                {getSeverityText(alert.severity)} • {formatTime(alert.timestamp)}
              </Caption>
            </View>
          </View>
          
          {/* 確認按鈕 */}
          {alert.id && !alert.acknowledged && onAcknowledgeAlert && (
            <TouchableOpacity
              style={styles.acknowledgeButton}
              onPress={() => onAcknowledgeAlert(alert.id!)}
            >
              <Text variant="caption" color={theme.colors.primary}>
                確認
              </Text>
            </TouchableOpacity>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  const stats = getAlertStats();
  const displayAlerts = alerts.slice(0, 3); // 只顯示前3個警報

  return (
    <Card elevation="md">
      {/* 卡片標題 */}
      <View style={styles.header}>
        <View style={styles.titleRow}>
          <Text variant="h4">系統警報</Text>
          {stats.total > 0 && (
            <View style={[
              styles.alertBadge, 
              { backgroundColor: stats.critical > 0 ? theme.colors.error : theme.colors.warning }
            ]}>
              <Text variant="caption" color="#FFFFFF">
                {stats.total}
              </Text>
            </View>
          )}
        </View>
        
        {onViewAllAlerts && stats.total > 0 && (
          <TouchableOpacity onPress={onViewAllAlerts}>
            <Text variant="caption" color={theme.colors.primary}>
              查看全部
            </Text>
          </TouchableOpacity>
        )}
      </View>

      {/* 警報統計 */}
      {stats.total > 0 && (
        <View style={styles.statsContainer}>
          {stats.critical > 0 && (
            <View style={styles.statItem}>
              <View style={[styles.statIndicator, { backgroundColor: theme.colors.error }]} />
              <Text variant="caption">{stats.critical} 危險</Text>
            </View>
          )}
          {stats.warning > 0 && (
            <View style={styles.statItem}>
              <View style={[styles.statIndicator, { backgroundColor: theme.colors.warning }]} />
              <Text variant="caption">{stats.warning} 警告</Text>
            </View>
          )}
          {stats.info > 0 && (
            <View style={styles.statItem}>
              <View style={[styles.statIndicator, { backgroundColor: theme.colors.info }]} />
              <Text variant="caption">{stats.info} 資訊</Text>
            </View>
          )}
        </View>
      )}

      {/* 警報列表 */}
      {stats.total > 0 ? (
        <View style={styles.alertsList}>
          {displayAlerts.map(renderAlertItem)}
          
          {alerts.length > 3 && (
            <View style={styles.moreAlertsIndicator}>
              <Text variant="caption" color={theme.colors.textSecondary}>
                還有 {alerts.length - 3} 個警報...
              </Text>
              {onViewAllAlerts && (
                <TouchableOpacity onPress={onViewAllAlerts}>
                  <Text variant="caption" color={theme.colors.primary}>
                    查看全部
                  </Text>
                </TouchableOpacity>
              )}
            </View>
          )}
        </View>
      ) : (
        /* 無警報狀態 */
        <View style={styles.noAlertsContainer}>
          <Text variant="h2" style={{ textAlign: 'center', marginBottom: 8 }}>
            ✅
          </Text>
          <Text 
            variant="body2" 
            color={theme.colors.textSecondary}
            style={{ textAlign: 'center' }}
          >
            系統運行正常，無活躍警報
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
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  alertBadge: {
    marginLeft: 8,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
    minWidth: 20,
    alignItems: 'center',
  },
  statsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 16,
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: 'rgba(0,0,0,0.02)',
    borderRadius: 8,
  },
  statItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
    marginVertical: 2,
  },
  statIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 4,
  },
  alertsList: {
    maxHeight: 200,
  },
  alertItem: {
    borderLeftWidth: 3,
    borderLeftColor: '#E0E0E0',
    marginVertical: 4,
    paddingLeft: 12,
    paddingVertical: 8,
  },
  alertHeader: {
    flex: 1,
  },
  alertTitleRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    flex: 1,
  },
  alertContent: {
    flex: 1,
    marginRight: 8,
  },
  acknowledgeButton: {
    position: 'absolute',
    right: 0,
    top: 0,
    paddingHorizontal: 8,
    paddingVertical: 4,
    backgroundColor: 'rgba(33, 150, 243, 0.1)',
    borderRadius: 4,
  },
  moreAlertsIndicator: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F0F0F0',
  },
  noAlertsContainer: {
    alignItems: 'center',
    paddingVertical: 32,
  },
});