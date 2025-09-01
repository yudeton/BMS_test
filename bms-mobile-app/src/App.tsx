import React, { useEffect, useState } from 'react';
import { StatusBar, Alert, AppState, AppStateStatus } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

// 服務初始化
import { initializeServices, shutdownServices } from './services/ServiceRegistry';

// 導航配置
import { RootNavigator } from './presentation/navigation/RootNavigator';

// 主題和樣式
import { ThemeProvider } from './presentation/theme/ThemeProvider';

// 錯誤邊界和載入畫面
import { ErrorBoundary } from './presentation/components/common/ErrorBoundary';
import { LoadingScreen } from './presentation/components/common/LoadingScreen';

/**
 * 應用根組件
 */
const App: React.FC = () => {
  const [isInitialized, setIsInitialized] = useState(false);
  const [initializationError, setInitializationError] = useState<string | null>(null);

  useEffect(() => {
    initializeApp();
    setupAppStateHandler();
    
    return () => {
      cleanupApp();
    };
  }, []);

  /**
   * 初始化應用
   */
  const initializeApp = async (): Promise<void> => {
    try {
      console.log('🚀 開始初始化 BMS 監控應用...');

      // 初始化服務
      await initializeServices();

      setIsInitialized(true);
      console.log('✅ BMS 監控應用初始化完成');

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '未知錯誤';
      console.error('❌ 應用初始化失敗:', errorMessage);
      
      setInitializationError(errorMessage);
      
      // 顯示錯誤對話框
      Alert.alert(
        '初始化失敗',
        `應用無法正常啟動：${errorMessage}`,
        [
          { text: '重試', onPress: () => retryInitialization() },
          { text: '退出', onPress: () => {/* TODO: 退出應用 */} }
        ]
      );
    }
  };

  /**
   * 重試初始化
   */
  const retryInitialization = (): void => {
    setInitializationError(null);
    setIsInitialized(false);
    initializeApp();
  };

  /**
   * 設置應用狀態監聽
   */
  const setupAppStateHandler = (): (() => void) => {
    const handleAppStateChange = (nextAppState: AppStateStatus) => {
      console.log(`📱 應用狀態變化: ${nextAppState}`);
      
      if (nextAppState === 'background') {
        // 應用進入背景
        console.log('📱 應用進入背景模式');
      } else if (nextAppState === 'active') {
        // 應用變為活躍
        console.log('📱 應用變為活躍模式');
      }
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    
    // 返回清理函數
    return () => {
      subscription?.remove();
    };
  };

  /**
   * 清理應用資源
   */
  const cleanupApp = async (): Promise<void> => {
    try {
      console.log('🧹 開始清理應用資源...');
      await shutdownServices();
      console.log('✅ 應用資源清理完成');
    } catch (error) {
      console.error('❌ 清理應用資源失敗:', error);
    }
  };

  /**
   * 渲染載入畫面
   */
  const renderLoadingScreen = (): JSX.Element => {
    return (
      <SafeAreaProvider>
        <ThemeProvider>
          <LoadingScreen 
            error={initializationError}
            onRetry={retryInitialization}
            loadingText="正在初始化 BMS 監控系統..."
          />
        </ThemeProvider>
      </SafeAreaProvider>
    );
  };

  /**
   * 渲染主應用
   */
  const renderMainApp = (): JSX.Element => {
    return (
      <SafeAreaProvider>
        <ThemeProvider>
          <ErrorBoundary>
            <NavigationContainer>
              <StatusBar 
                barStyle="light-content" 
                backgroundColor="#1a1a1a" 
              />
              <RootNavigator />
            </NavigationContainer>
          </ErrorBoundary>
        </ThemeProvider>
      </SafeAreaProvider>
    );
  };

  // 根據初始化狀態渲染不同內容
  if (!isInitialized || initializationError) {
    return renderLoadingScreen();
  }

  return renderMainApp();
};

// LoadingScreen 組件已經在 common 資料夾中實作

export default App;