module.exports = {
  presets: ['module:metro-react-native-babel-preset'],
  plugins: [
    // 實驗性裝飾器支援（用於 MobX 和 TSyringe）
    ['@babel/plugin-proposal-decorators', { legacy: true }],
    
    // Class properties 支援
    ['@babel/plugin-proposal-class-properties', { loose: true }],
    
    // 模組路徑別名支援
    [
      'module-resolver',
      {
        root: ['./src'],
        alias: {
          '@': './src',
          '@services': './src/services',
          '@domain': './src/domain',
          '@presentation': './src/presentation',
          '@utils': './src/utils',
        },
      },
    ],
    
    // React Native Reanimated 支援（如果需要動畫）
    'react-native-reanimated/plugin',
  ],
};