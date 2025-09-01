import React, { useEffect } from 'react';
import { View, ScrollView, RefreshControl, StyleSheet, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { observer } from 'mobx-react-lite';

// 基礎組件
import { Text } from '../components/common/Text';
import { Button } from '../components/common/Button';

// 電池專用組件
import { BatteryStatusCard } from '../components/battery/BatteryStatusCard';
import { AlertsCard } from '../components/battery/AlertsCard';

// 主題和樣式
import { useThemeOnly } from '../theme/ThemeProvider';

// ViewModel (暫時使用 mock 資料，實際應該透過依賴注入獲取)
import { DashboardViewModel } from '../viewmodels/DashboardViewModel';

/**
 * 儀表板畫面組件屬性
 */
interface DashboardScreenProps {
  navigation?: any; // React Navigation 的 navigation prop
}

/**
 * 儀表板畫面組件
 * 顯示電池監控的主要資訊和控制功能
 */
export const DashboardScreen: React.FC<DashboardScreenProps> = observer(({ navigation }) => {
  const theme = useThemeOnly();
  
  // TODO: 實際應該透過依賴注入獲取 ViewModel
  // const viewModel = useViewModel<DashboardViewModel>();
  // 暫時建立 mock ViewModel
  const viewModel = React.useMemo(() => {
    // 這裡需要實際的 use case 實例
    // return new DashboardViewModel(monitorBatteryUseCase, handleAlertsUseCase);
    return {
      // Mock 數據和方法
      batteryData: null,
      isMonitoring: false,
      connectionStatus: 'disconnected',
      activeAlerts: [],
      isLoading: false,
      error: null,
      startMonitoring: async () => console.log('開始監控'),
      stopMonitoring: async () => console.log('停止監控'),
      refreshBatteryData: async () => console.log('刷新數據'),
      acknowledgeAlert: async (id: number) => console.log('確認警報', id),
      retry: async () => console.log('重試'),
    };
  }, []);

  /**
   * 組件掛載時初始化
   */
  useEffect(() => {
    // 初始化邏輯
    console.log('儀表板畫面已載入');
    
    // 清理函數
    return () => {
      console.log('儀表板畫面卸載');
    };
  }, []);

  /**
   * 處理監控狀態切換
   */
  const handleMonitoringToggle = async (): Promise<void> => {
    try {
      if (viewModel.isMonitoring) {
        await viewModel.stopMonitoring();
      } else {
        await viewModel.startMonitoring();
      }
    } catch (error) {
      console.error('監控狀態切換失敗:', error);
      Alert.alert('錯誤', '監控狀態切換失敗');
    }
  };

  /**
   * 處理數據刷新
   */
  const handleRefresh = async (): Promise<void> => {
    try {
      await viewModel.refreshBatteryData();
    } catch (error) {
      console.error('刷新數據失敗:', error);
    }
  };

  /**
   * 處理警報確認
   */
  const handleAcknowledgeAlert = async (alertId: number): Promise<void> => {
    try {
      await viewModel.acknowledgeAlert(alertId);
    } catch (error) {
      console.error('確認警報失敗:', error);
      Alert.alert('錯誤', '確認警報失敗');
    }
  };

  /**
   * 處理錯誤重試
   */
  const handleRetry = async (): Promise<void> => {
    try {
      await viewModel.retry();
    } catch (error) {
      console.error('重試失敗:', error);
    }
  };

  /**
   * 導航到警報頁面
   */
  const navigateToAlerts = (): void => {
    navigation?.navigate('Alerts');
  };

  /**
   * 導航到設定頁面
   */
  const navigateToSettings = (): void => {
    navigation?.navigate('Settings');
  };

  /**
   * 渲染標題列
   */
  const renderHeader = (): JSX.Element => {
    return (
      <View style={styles.header}>
        <View>
          <Text variant="h2">BMS 監控</Text>
          <Text variant="body2" color={theme.colors.textSecondary}>
            電池管理系統
          </Text>
        </View>
        
        <View style={styles.headerActions}>
          {/* 設定按鈕 */}
          <Button
            title="設定"
            onPress={navigateToSettings}
            variant="ghost"
            size="small"
          />
        </View>
      </View>
    );
  };

  /**
   * 渲染控制面板
   */
  const renderControlPanel = (): JSX.Element => {
    return (
      <View style={styles.controlPanel}>
        <Button
          title={viewModel.isMonitoring ? '停止監控' : '開始監控'}
          onPress={handleMonitoringToggle}
          variant={viewModel.isMonitoring ? 'danger' : 'primary'}
          loading={viewModel.isLoading}
          fullWidth
          size="large"
        />
        
        {viewModel.isMonitoring && (
          <Button
            title="刷新數據"
            onPress={handleRefresh}
            variant="outline"
            loading={viewModel.isLoading}
            style={{ marginTop: theme.spacing.md }}
            fullWidth
          />
        )}
      </View>
    );
  };

  /**
   * 渲染錯誤狀態
   */
  const renderErrorState = (): JSX.Element => {
    return (
      <View style={styles.errorContainer}>
        <Text variant="h3" style={{ textAlign: 'center', marginBottom: 16 }}>
          ⚠️ 發生錯誤
        </Text>
        <Text 
          variant="body1" 
          color={theme.colors.textSecondary}
          style={{ textAlign: 'center', marginBottom: 24 }}
        >
          {viewModel.error || '未知錯誤'}
        </Text>
        <Button
          title="重試"
          onPress={handleRetry}
          variant="primary"
          loading={viewModel.isLoading}
        />
      </View>
    );
  };

  /**
   * 渲染主要內容
   */
  const renderContent = (): JSX.Element => {
    if (viewModel.error) {
      return renderErrorState();
    }

    return (
      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl
            refreshing={viewModel.isLoading}
            onRefresh={handleRefresh}
            colors={[theme.colors.primary]}
            tintColor={theme.colors.primary}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.content}>
          {/* 電池狀態卡片 */}
          <BatteryStatusCard
            batteryData={viewModel.batteryData}
            connectionStatus={viewModel.connectionStatus as any}
            onPress={() => console.log('電池狀態卡片被點擊')}
          />

          {/* 系統警報卡片 */}
          <AlertsCard
            alerts={viewModel.activeAlerts}
            onViewAllAlerts={navigateToAlerts}
            onAcknowledgeAlert={handleAcknowledgeAlert}
            onAlertPress={(alert) => console.log('警報被點擊:', alert)}
          />

          {/* 控制面板 */}
          {renderControlPanel()}

          {/* 底部間距 */}
          <View style={{ height: theme.spacing.xl }} />
        </View>
      </ScrollView>
    );
  };

  return (
    <SafeAreaView 
      style={[styles.container, { backgroundColor: theme.colors.background }]}
      edges={['top']}
    >
      {renderHeader()}
      {renderContent()}
    </SafeAreaView>
  );
});

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 20,
    gap: 20,
  },
  controlPanel: {
    marginTop: 8,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
});