import React from 'react';
import { View, StyleSheet, ActivityIndicator } from 'react-native';
import { Text } from './Text';
import { Button } from './Button';
import { Card } from './Card';
import { useThemeOnly } from '../../theme/ThemeProvider';

/**
 * 載入畫面組件屬性
 */
interface LoadingScreenProps {
  error?: string | null;
  onRetry?: () => void;
  loadingText?: string;
}

/**
 * 載入畫面組件
 * 顯示應用初始化載入狀態和錯誤處理
 */
export const LoadingScreen: React.FC<LoadingScreenProps> = ({
  error,
  onRetry,
  loadingText = '正在初始化 BMS 監控系統...',
}) => {
  const theme = useThemeOnly();

  const renderContent = (): JSX.Element => {
    if (error) {
      return (
        <Card style={styles.errorCard}>
          <View style={theme.layout.center}>
            {/* 錯誤圖標 */}
            <View style={[styles.iconContainer, { backgroundColor: theme.colors.error }]}>
              <Text variant="h2" color="#FFFFFF">
                ⚠️
              </Text>
            </View>
            
            {/* 錯誤標題 */}
            <Text 
              variant="h3" 
              style={[theme.layout.marginVertical('md'), { textAlign: 'center' }]}
            >
              初始化失敗
            </Text>
            
            {/* 錯誤訊息 */}
            <Text 
              variant="body1" 
              color={theme.colors.textSecondary}
              style={[theme.layout.marginVertical('sm'), { textAlign: 'center' }]}
            >
              {error}
            </Text>
            
            {/* 重試按鈕 */}
            {onRetry && (
              <Button
                title="重試"
                onPress={onRetry}
                variant="primary"
                style={theme.layout.marginVertical('md')}
              />
            )}
            
            {/* 幫助文字 */}
            <Text 
              variant="caption" 
              color={theme.colors.textSecondary}
              style={{ textAlign: 'center', marginTop: theme.spacing.md }}
            >
              請確保藍牙已開啟並授予必要權限
            </Text>
          </View>
        </Card>
      );
    }

    return (
      <View style={theme.layout.center}>
        {/* 應用圖標 */}
        <View style={[styles.iconContainer, { backgroundColor: theme.colors.primary }]}>
          <Text variant="h1" color="#FFFFFF">
            🔋
          </Text>
        </View>
        
        {/* 應用名稱 */}
        <Text 
          variant="h2" 
          style={[theme.layout.marginVertical('md'), { textAlign: 'center' }]}
        >
          BMS 監控
        </Text>
        
        {/* 載入指示器 */}
        <ActivityIndicator 
          size="large" 
          color={theme.colors.primary}
          style={theme.layout.marginVertical('lg')}
        />
        
        {/* 載入文字 */}
        <Text 
          variant="body1" 
          color={theme.colors.textSecondary}
          style={{ textAlign: 'center', marginTop: theme.spacing.md }}
        >
          {loadingText}
        </Text>
        
        {/* 版本資訊 */}
        <Text 
          variant="caption" 
          color={theme.colors.textSecondary}
          style={{ 
            textAlign: 'center', 
            position: 'absolute', 
            bottom: theme.spacing.xl 
          }}
        >
          版本 1.0.0
        </Text>
      </View>
    );
  };

  return (
    <View 
      style={[
        styles.container, 
        { backgroundColor: theme.colors.background }
      ]}
    >
      {renderContent()}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  errorCard: {
    width: '100%',
    maxWidth: 400,
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
});