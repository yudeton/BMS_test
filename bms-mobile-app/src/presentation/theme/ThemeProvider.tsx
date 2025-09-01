import React, { createContext, useContext, useState, useEffect } from 'react';
import { Appearance, ColorSchemeName } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// 主題配置
import { ColorTheme, lightTheme, darkTheme } from './colors';
import { Typography, typography } from './typography';
import { spacing, borderRadius, shadows, layout } from './spacing';

/**
 * 主題類型
 */
export type ThemeMode = 'light' | 'dark' | 'auto';

/**
 * 完整主題介面
 */
export interface Theme {
  colors: ColorTheme;
  typography: Typography;
  spacing: typeof spacing;
  borderRadius: typeof borderRadius;
  shadows: typeof shadows;
  layout: typeof layout;
  isDark: boolean;
}

/**
 * 主題上下文介面
 */
interface ThemeContextType {
  theme: Theme;
  themeMode: ThemeMode;
  setThemeMode: (mode: ThemeMode) => void;
  toggleTheme: () => void;
}

/**
 * 主題上下文
 */
const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

/**
 * 主題配置鍵
 */
const THEME_STORAGE_KEY = '@BMSApp:theme';

/**
 * 主題提供者組件
 */
interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: ThemeMode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ 
  children, 
  defaultTheme = 'auto' 
}) => {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(defaultTheme);
  const [systemColorScheme, setSystemColorScheme] = useState<ColorSchemeName>(
    Appearance.getColorScheme()
  );

  /**
   * 初始化主題設定
   */
  useEffect(() => {
    loadSavedTheme();
    setupSystemThemeListener();
  }, []);

  /**
   * 載入已保存的主題設定
   */
  const loadSavedTheme = async (): Promise<void> => {
    try {
      const savedTheme = await AsyncStorage.getItem(THEME_STORAGE_KEY);
      if (savedTheme && ['light', 'dark', 'auto'].includes(savedTheme)) {
        setThemeModeState(savedTheme as ThemeMode);
      }
    } catch (error) {
      console.error('載入主題設定失敗:', error);
    }
  };

  /**
   * 設置系統主題監聽器
   */
  const setupSystemThemeListener = (): void => {
    const subscription = Appearance.addChangeListener(({ colorScheme }) => {
      setSystemColorScheme(colorScheme);
    });

    return () => {
      subscription?.remove();
    };
  };

  /**
   * 設置主題模式
   */
  const setThemeMode = async (mode: ThemeMode): Promise<void> => {
    try {
      setThemeModeState(mode);
      await AsyncStorage.setItem(THEME_STORAGE_KEY, mode);
      console.log(`主題已切換至: ${mode}`);
    } catch (error) {
      console.error('保存主題設定失敗:', error);
    }
  };

  /**
   * 切換主題（明暗切換）
   */
  const toggleTheme = (): void => {
    const newMode = themeMode === 'light' ? 'dark' : 'light';
    setThemeMode(newMode);
  };

  /**
   * 計算當前實際主題
   */
  const getCurrentTheme = (): Theme => {
    let isDark = false;

    switch (themeMode) {
      case 'light':
        isDark = false;
        break;
      case 'dark':
        isDark = true;
        break;
      case 'auto':
        isDark = systemColorScheme === 'dark';
        break;
    }

    const colors = isDark ? darkTheme : lightTheme;

    return {
      colors,
      typography,
      spacing,
      borderRadius,
      shadows,
      layout,
      isDark,
    };
  };

  const theme = getCurrentTheme();

  const contextValue: ThemeContextType = {
    theme,
    themeMode,
    setThemeMode,
    toggleTheme,
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
};

/**
 * 使用主題的 Hook
 */
export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  
  return context;
};

/**
 * 僅獲取主題物件的 Hook
 */
export const useThemeOnly = (): Theme => {
  const { theme } = useTheme();
  return theme;
};