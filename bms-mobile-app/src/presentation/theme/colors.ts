/**
 * 應用程式色彩配置
 * 支援明暗主題切換
 */

export interface ColorTheme {
  // 主要色彩
  primary: string;
  primaryDark: string;
  primaryLight: string;
  secondary: string;
  
  // 背景色彩
  background: string;
  surface: string;
  card: string;
  
  // 文字色彩
  text: string;
  textSecondary: string;
  textDisabled: string;
  
  // 狀態色彩
  success: string;
  warning: string;
  error: string;
  info: string;
  
  // 電池狀態專用色彩
  batteryGood: string;
  batteryWarning: string;
  batteryCritical: string;
  batteryCharging: string;
  
  // 邊框和分隔線
  border: string;
  separator: string;
  
  // 覆蓋層
  overlay: string;
  backdrop: string;
  
  // 電量色彩漸變
  socGradient: {
    high: string;    // 70-100%
    medium: string;  // 30-70%
    low: string;     // 0-30%
  };
}

/**
 * 明亮主題
 */
export const lightTheme: ColorTheme = {
  // 主要色彩 - 使用電池綠色系
  primary: '#4CAF50',
  primaryDark: '#388E3C',
  primaryLight: '#81C784',
  secondary: '#2196F3',
  
  // 背景色彩
  background: '#FAFAFA',
  surface: '#FFFFFF',
  card: '#FFFFFF',
  
  // 文字色彩
  text: '#212121',
  textSecondary: '#757575',
  textDisabled: '#BDBDBD',
  
  // 狀態色彩
  success: '#4CAF50',
  warning: '#FF9800',
  error: '#F44336',
  info: '#2196F3',
  
  // 電池狀態專用色彩
  batteryGood: '#4CAF50',
  batteryWarning: '#FF9800',
  batteryCritical: '#F44336',
  batteryCharging: '#2196F3',
  
  // 邊框和分隔線
  border: '#E0E0E0',
  separator: '#F5F5F5',
  
  // 覆蓋層
  overlay: 'rgba(0, 0, 0, 0.5)',
  backdrop: 'rgba(0, 0, 0, 0.3)',
  
  // 電量色彩漸變
  socGradient: {
    high: '#4CAF50',    // 綠色 - 健康
    medium: '#FF9800',  // 橙色 - 注意
    low: '#F44336'      // 紅色 - 危險
  }
};

/**
 * 暗黑主題
 */
export const darkTheme: ColorTheme = {
  // 主要色彩
  primary: '#66BB6A',
  primaryDark: '#4CAF50',
  primaryLight: '#81C784',
  secondary: '#42A5F5',
  
  // 背景色彩
  background: '#121212',
  surface: '#1E1E1E',
  card: '#2C2C2C',
  
  // 文字色彩
  text: '#FFFFFF',
  textSecondary: '#B0B0B0',
  textDisabled: '#666666',
  
  // 狀態色彩
  success: '#66BB6A',
  warning: '#FFA726',
  error: '#EF5350',
  info: '#42A5F5',
  
  // 電池狀態專用色彩
  batteryGood: '#66BB6A',
  batteryWarning: '#FFA726',
  batteryCritical: '#EF5350',
  batteryCharging: '#42A5F5',
  
  // 邊框和分隔線
  border: '#404040',
  separator: '#333333',
  
  // 覆蓋層
  overlay: 'rgba(0, 0, 0, 0.7)',
  backdrop: 'rgba(0, 0, 0, 0.5)',
  
  // 電量色彩漸變
  socGradient: {
    high: '#66BB6A',
    medium: '#FFA726',
    low: '#EF5350'
  }
};

/**
 * 根據 SOC 值獲取對應的色彩
 * @param soc 電量百分比 (0-100)
 * @param theme 主題配置
 * @returns 對應的色彩
 */
export const getSOCColor = (soc: number, theme: ColorTheme): string => {
  if (soc >= 70) return theme.socGradient.high;
  if (soc >= 30) return theme.socGradient.medium;
  return theme.socGradient.low;
};

/**
 * 根據電池狀態獲取色彩
 * @param status 電池狀態
 * @param theme 主題配置
 * @returns 對應的色彩
 */
export const getBatteryStatusColor = (
  status: 'normal' | 'warning' | 'critical' | 'charging', 
  theme: ColorTheme
): string => {
  switch (status) {
    case 'normal': return theme.batteryGood;
    case 'warning': return theme.batteryWarning;
    case 'critical': return theme.batteryCritical;
    case 'charging': return theme.batteryCharging;
    default: return theme.text;
  }
};

/**
 * 生成透明度色彩
 * @param color 基礎色彩
 * @param alpha 透明度 (0-1)
 * @returns 帶透明度的色彩
 */
export const withAlpha = (color: string, alpha: number): string => {
  // 簡單實作，實際應用中可使用 color 庫
  if (color.startsWith('#')) {
    const hex = color.slice(1);
    if (hex.length === 6) {
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
  }
  return color;
};