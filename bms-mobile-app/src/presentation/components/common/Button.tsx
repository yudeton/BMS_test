import React from 'react';
import { TouchableOpacity, View, StyleSheet, ViewStyle, ActivityIndicator } from 'react-native';
import { Text } from './Text';
import { useThemeOnly } from '../../theme/ThemeProvider';

/**
 * 按鈕變體
 */
type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';

/**
 * 按鈕大小
 */
type ButtonSize = 'small' | 'medium' | 'large';

/**
 * 按鈕組件屬性
 */
interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  style?: ViewStyle;
  fullWidth?: boolean;
}

/**
 * 按鈕組件
 * 提供多種樣式變體的統一按鈕組件
 */
export const Button: React.FC<ButtonProps> = ({
  title,
  onPress,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  loading = false,
  icon,
  iconPosition = 'left',
  style,
  fullWidth = false,
}) => {
  const theme = useThemeOnly();

  /**
   * 獲取按鈕樣式
   */
  const getButtonStyle = (): ViewStyle => {
    const baseStyle: ViewStyle = {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      ...theme.layout.borderRadius('md'),
    };

    // 大小樣式
    const sizeStyles: Record<ButtonSize, ViewStyle> = {
      small: {
        ...theme.layout.paddingHorizontal('md'),
        ...theme.layout.paddingVertical('sm'),
        minHeight: 36,
      },
      medium: {
        ...theme.layout.paddingHorizontal('lg'),
        ...theme.layout.paddingVertical('md'),
        minHeight: 44,
      },
      large: {
        ...theme.layout.paddingHorizontal('xl'),
        ...theme.layout.paddingVertical('lg'),
        minHeight: 52,
      },
    };

    // 變體樣式
    const variantStyles: Record<ButtonVariant, ViewStyle> = {
      primary: {
        backgroundColor: theme.colors.primary,
        ...theme.layout.shadow('sm', theme.colors.text),
      },
      secondary: {
        backgroundColor: theme.colors.secondary,
        ...theme.layout.shadow('sm', theme.colors.text),
      },
      outline: {
        backgroundColor: 'transparent',
        ...theme.layout.border('thin', theme.colors.primary),
      },
      ghost: {
        backgroundColor: 'transparent',
      },
      danger: {
        backgroundColor: theme.colors.error,
        ...theme.layout.shadow('sm', theme.colors.text),
      },
    };

    // 禁用狀態樣式
    const disabledStyle: ViewStyle = disabled ? {
      backgroundColor: theme.colors.textDisabled,
      opacity: 0.6,
    } : {};

    // 全寬樣式
    const fullWidthStyle: ViewStyle = fullWidth ? {
      width: '100%',
    } : {};

    return {
      ...baseStyle,
      ...sizeStyles[size],
      ...variantStyles[variant],
      ...disabledStyle,
      ...fullWidthStyle,
      ...style,
    };
  };

  /**
   * 獲取文字顏色
   */
  const getTextColor = (): string => {
    if (disabled) {
      return theme.colors.textDisabled;
    }

    switch (variant) {
      case 'primary':
      case 'secondary':
      case 'danger':
        return '#FFFFFF';
      case 'outline':
        return theme.colors.primary;
      case 'ghost':
        return theme.colors.primary;
      default:
        return theme.colors.text;
    }
  };

  /**
   * 獲取圖標大小
   */
  const getIconSize = (): number => {
    switch (size) {
      case 'small': return 16;
      case 'medium': return 20;
      case 'large': return 24;
    }
  };

  /**
   * 渲染按鈕內容
   */
  const renderContent = (): JSX.Element => {
    const textColor = getTextColor();
    const iconSize = getIconSize();

    if (loading) {
      return (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="small" color={textColor} />
          <Text 
            variant="button" 
            color={textColor}
            style={{ marginLeft: theme.spacing.sm }}
          >
            載入中...
          </Text>
        </View>
      );
    }

    return (
      <View style={styles.contentContainer}>
        {icon && iconPosition === 'left' && (
          <View style={{ marginRight: theme.spacing.sm }}>
            {icon}
          </View>
        )}
        
        <Text variant="button" color={textColor}>
          {title}
        </Text>
        
        {icon && iconPosition === 'right' && (
          <View style={{ marginLeft: theme.spacing.sm }}>
            {icon}
          </View>
        )}
      </View>
    );
  };

  return (
    <TouchableOpacity
      style={getButtonStyle()}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.7}
    >
      {renderContent()}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  contentContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
});