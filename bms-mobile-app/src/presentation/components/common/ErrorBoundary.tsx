import React, { Component, ErrorInfo, ReactNode } from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from './Text';
import { Button } from './Button';
import { Card } from './Card';

/**
 * 錯誤邊界組件屬性
 */
interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, retry: () => void) => ReactNode;
}

/**
 * 錯誤邊界組件狀態
 */
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * 錯誤邊界組件
 * 捕獲並處理 React 組件樹中的 JavaScript 錯誤
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  /**
   * 捕獲錯誤時呼叫
   */
  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  /**
   * 錯誤被捕獲後呼叫
   */
  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('錯誤邊界捕獲到錯誤:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
    });

    // 這裡可以將錯誤資訊發送到錯誤監控服務
    // 例如：Sentry, Bugsnag 等
    this.logErrorToService(error, errorInfo);
  }

  /**
   * 記錄錯誤到監控服務
   */
  private logErrorToService(error: Error, errorInfo: ErrorInfo): void {
    try {
      // TODO: 整合錯誤監控服務
      const errorData = {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
      };
      
      console.error('應用錯誤詳情:', errorData);
      
      // 這裡可以發送到外部服務
      // crashlytics().recordError(error);
      // Sentry.captureException(error);
      
    } catch (loggingError) {
      console.error('記錄錯誤失敗:', loggingError);
    }
  }

  /**
   * 重試操作
   */
  private handleRetry = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  /**
   * 渲染錯誤 UI
   */
  private renderErrorUI(): ReactNode {
    const { fallback } = this.props;
    const { error } = this.state;

    // 如果提供了自訂 fallback，使用它
    if (fallback && error) {
      return fallback(error, this.handleRetry);
    }

    // 預設錯誤 UI
    return (
      <View style={styles.container}>
        <Card style={styles.errorCard}>
          <View style={styles.content}>
            {/* 錯誤圖標 */}
            <View style={styles.iconContainer}>
              <Text variant="h1">💥</Text>
            </View>
            
            {/* 錯誤標題 */}
            <Text variant="h3" style={styles.title}>
              應用程式發生錯誤
            </Text>
            
            {/* 錯誤描述 */}
            <Text variant="body1" style={styles.description}>
              很抱歉，應用程式遇到了未預期的錯誤。
              請嘗試重新啟動應用程式。
            </Text>
            
            {/* 錯誤詳情（僅在開發模式下顯示） */}
            {__DEV__ && error && (
              <View style={styles.errorDetails}>
                <Text variant="label" style={styles.errorLabel}>
                  錯誤詳情：
                </Text>
                <Text variant="caption" style={styles.errorMessage}>
                  {error.message}
                </Text>
                {error.stack && (
                  <Text variant="caption" style={styles.errorStack}>
                    {error.stack.substring(0, 500)}...
                  </Text>
                )}
              </View>
            )}
            
            {/* 操作按鈕 */}
            <View style={styles.actions}>
              <Button
                title="重試"
                onPress={this.handleRetry}
                variant="primary"
                style={styles.retryButton}
              />
            </View>
          </View>
        </Card>
      </View>
    );
  }

  render(): ReactNode {
    const { hasError } = this.state;
    const { children } = this.props;

    if (hasError) {
      return this.renderErrorUI();
    }

    return children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#F5F5F5',
  },
  errorCard: {
    width: '100%',
    maxWidth: 400,
  },
  content: {
    alignItems: 'center',
  },
  iconContainer: {
    marginBottom: 16,
  },
  title: {
    textAlign: 'center',
    marginBottom: 12,
  },
  description: {
    textAlign: 'center',
    marginBottom: 20,
    lineHeight: 24,
  },
  errorDetails: {
    width: '100%',
    marginBottom: 20,
    padding: 12,
    backgroundColor: '#FFF5F5',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#FED7D7',
  },
  errorLabel: {
    marginBottom: 8,
    color: '#C53030',
  },
  errorMessage: {
    marginBottom: 8,
    color: '#E53E3E',
    fontFamily: 'monospace',
  },
  errorStack: {
    color: '#C53030',
    fontFamily: 'monospace',
    fontSize: 11,
  },
  actions: {
    width: '100%',
  },
  retryButton: {
    width: '100%',
  },
});