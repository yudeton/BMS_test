/**
 * BMS 監控應用程式入口點
 */

import { AppRegistry } from 'react-native';
import App from './src/App';
import { name as appName } from './package.json';

// 註冊根組件
AppRegistry.registerComponent(appName, () => App);