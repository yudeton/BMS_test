/**
 * 文字排版配置
 */

import { TextStyle } from 'react-native';

export interface Typography {
  // 標題樣式
  h1: TextStyle;
  h2: TextStyle;
  h3: TextStyle;
  h4: TextStyle;
  h5: TextStyle;
  h6: TextStyle;
  
  // 內文樣式
  body1: TextStyle;
  body2: TextStyle;
  
  // 說明文字
  caption: TextStyle;
  
  // 按鈕文字
  button: TextStyle;
  
  // 數據顯示專用
  dataLarge: TextStyle;   // 大數據顯示（如電壓值）
  dataMedium: TextStyle;  // 中等數據顯示
  dataSmall: TextStyle;   // 小數據顯示
  
  // 標籤樣式
  label: TextStyle;
  
  // 單位樣式
  unit: TextStyle;
}

/**
 * 基礎字體配置
 */
const baseFonts = {
  regular: 'System',
  medium: 'System',
  bold: 'System',
  light: 'System',
};

/**
 * 字體大小配置
 */
const fontSizes = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 18,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  huge: 48,
};

/**
 * 行高配置
 */
const lineHeights = {
  tight: 1.2,
  normal: 1.4,
  loose: 1.6,
};

/**
 * 字重配置
 */
const fontWeights = {
  light: '300' as const,
  normal: '400' as const,
  medium: '500' as const,
  semibold: '600' as const,
  bold: '700' as const,
};

/**
 * 文字排版樣式定義
 */
export const typography: Typography = {
  // 標題樣式
  h1: {
    fontFamily: baseFonts.bold,
    fontSize: fontSizes.xxxl,
    fontWeight: fontWeights.bold,
    lineHeight: fontSizes.xxxl * lineHeights.tight,
    letterSpacing: -0.5,
  },
  
  h2: {
    fontFamily: baseFonts.bold,
    fontSize: fontSizes.xxl,
    fontWeight: fontWeights.bold,
    lineHeight: fontSizes.xxl * lineHeights.tight,
    letterSpacing: -0.25,
  },
  
  h3: {
    fontFamily: baseFonts.medium,
    fontSize: fontSizes.xl,
    fontWeight: fontWeights.semibold,
    lineHeight: fontSizes.xl * lineHeights.normal,
  },
  
  h4: {
    fontFamily: baseFonts.medium,
    fontSize: fontSizes.lg,
    fontWeight: fontWeights.semibold,
    lineHeight: fontSizes.lg * lineHeights.normal,
  },
  
  h5: {
    fontFamily: baseFonts.medium,
    fontSize: fontSizes.md,
    fontWeight: fontWeights.medium,
    lineHeight: fontSizes.md * lineHeights.normal,
  },
  
  h6: {
    fontFamily: baseFonts.medium,
    fontSize: fontSizes.sm,
    fontWeight: fontWeights.medium,
    lineHeight: fontSizes.sm * lineHeights.normal,
  },
  
  // 內文樣式
  body1: {
    fontFamily: baseFonts.regular,
    fontSize: fontSizes.md,
    fontWeight: fontWeights.normal,
    lineHeight: fontSizes.md * lineHeights.loose,
  },
  
  body2: {
    fontFamily: baseFonts.regular,
    fontSize: fontSizes.sm,
    fontWeight: fontWeights.normal,
    lineHeight: fontSizes.sm * lineHeights.loose,
  },
  
  // 說明文字
  caption: {
    fontFamily: baseFonts.regular,
    fontSize: fontSizes.xs,
    fontWeight: fontWeights.normal,
    lineHeight: fontSizes.xs * lineHeights.normal,
    opacity: 0.7,
  },
  
  // 按鈕文字
  button: {
    fontFamily: baseFonts.medium,
    fontSize: fontSizes.md,
    fontWeight: fontWeights.medium,
    lineHeight: fontSizes.md * lineHeights.normal,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  
  // 數據顯示專用樣式
  dataLarge: {
    fontFamily: baseFonts.bold,
    fontSize: fontSizes.huge,
    fontWeight: fontWeights.bold,
    lineHeight: fontSizes.huge * lineHeights.tight,
    letterSpacing: -1,
  },
  
  dataMedium: {
    fontFamily: baseFonts.medium,
    fontSize: fontSizes.xxl,
    fontWeight: fontWeights.semibold,
    lineHeight: fontSizes.xxl * lineHeights.tight,
  },
  
  dataSmall: {
    fontFamily: baseFonts.medium,
    fontSize: fontSizes.lg,
    fontWeight: fontWeights.medium,
    lineHeight: fontSizes.lg * lineHeights.normal,
  },
  
  // 標籤樣式
  label: {
    fontFamily: baseFonts.medium,
    fontSize: fontSizes.sm,
    fontWeight: fontWeights.medium,
    lineHeight: fontSizes.sm * lineHeights.normal,
    textTransform: 'uppercase',
    letterSpacing: 0.3,
  },
  
  // 單位樣式
  unit: {
    fontFamily: baseFonts.regular,
    fontSize: fontSizes.sm,
    fontWeight: fontWeights.normal,
    lineHeight: fontSizes.sm * lineHeights.normal,
    opacity: 0.8,
  },
};