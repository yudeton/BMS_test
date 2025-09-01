import React from 'react';
import { Text as RNText, TextStyle, TextProps as RNTextProps } from 'react-native';
import { useThemeOnly } from '../../theme/ThemeProvider';
import type { Typography } from '../../theme/typography';

/**
 * 文字組件屬性
 */
interface TextProps extends Omit<RNTextProps, 'style'> {
  children: React.ReactNode;
  variant?: keyof Typography;
  color?: string;
  style?: TextStyle;
  center?: boolean;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  opacity?: number;
}

/**
 * 文字組件
 * 基於主題系統的統一文字組件
 */
export const Text: React.FC<TextProps> = ({
  children,
  variant = 'body1',
  color,
  style,
  center = false,
  bold = false,
  italic = false,
  underline = false,
  opacity,
  ...props
}) => {
  const theme = useThemeOnly();

  const textStyle: TextStyle = {
    ...theme.typography[variant],
    color: color || theme.colors.text,
    textAlign: center ? 'center' : undefined,
    fontWeight: bold ? 'bold' : theme.typography[variant].fontWeight,
    fontStyle: italic ? 'italic' : 'normal',
    textDecorationLine: underline ? 'underline' : 'none',
    opacity: opacity !== undefined ? opacity : 1,
    ...style,
  };

  return (
    <RNText style={textStyle} {...props}>
      {children}
    </RNText>
  );
};

/**
 * 標題組件快捷方式
 */
export const Heading: React.FC<Omit<TextProps, 'variant'> & { level?: 1 | 2 | 3 | 4 | 5 | 6 }> = ({ 
  level = 1, 
  ...props 
}) => {
  const variant = `h${level}` as keyof Typography;
  return <Text variant={variant} {...props} />;
};

/**
 * 數據顯示組件
 */
export const DataText: React.FC<Omit<TextProps, 'variant'> & { 
  size?: 'large' | 'medium' | 'small';
  unit?: string;
}> = ({ 
  size = 'medium', 
  unit,
  children,
  style,
  ...props 
}) => {
  const theme = useThemeOnly();
  const variant = size === 'large' ? 'dataLarge' : 
                  size === 'medium' ? 'dataMedium' : 
                  'dataSmall';

  return (
    <React.Fragment>
      <Text variant={variant} style={style} {...props}>
        {children}
      </Text>
      {unit && (
        <Text 
          variant="unit" 
          style={{ marginLeft: theme.spacing.xs }}
          color={theme.colors.textSecondary}
        >
          {unit}
        </Text>
      )}
    </React.Fragment>
  );
};

/**
 * 標籤組件
 */
export const Label: React.FC<Omit<TextProps, 'variant'>> = (props) => {
  return <Text variant="label" {...props} />;
};

/**
 * 說明文字組件
 */
export const Caption: React.FC<Omit<TextProps, 'variant'>> = (props) => {
  return <Text variant="caption" {...props} />;
};