import React from 'react';
import { View, ViewStyle, StyleSheet } from 'react-native';
import { useThemeOnly } from '../../theme/ThemeProvider';

/**
 * 卡片組件屬性
 */
interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  padding?: keyof typeof import('../../theme/spacing').spacing;
  elevation?: keyof typeof import('../../theme/spacing').shadows;
  borderRadius?: keyof typeof import('../../theme/spacing').borderRadius;
  backgroundColor?: string;
  onPress?: () => void;
}

/**
 * 卡片組件
 * 提供一致的卡片樣式和陰影效果
 */
export const Card: React.FC<CardProps> = ({
  children,
  style,
  padding = 'md',
  elevation = 'md',
  borderRadius = 'lg',
  backgroundColor,
  onPress,
}) => {
  const theme = useThemeOnly();

  const cardStyle: ViewStyle = {
    backgroundColor: backgroundColor || theme.colors.card,
    ...theme.layout.padding(padding),
    ...theme.layout.borderRadius(borderRadius),
    ...theme.layout.shadow(elevation, theme.colors.text),
    ...style,
  };

  if (onPress) {
    // TODO: 如果需要點擊效果，可以使用 TouchableOpacity
    return (
      <View style={cardStyle} onTouchEnd={onPress}>
        {children}
      </View>
    );
  }

  return (
    <View style={cardStyle}>
      {children}
    </View>
  );
};