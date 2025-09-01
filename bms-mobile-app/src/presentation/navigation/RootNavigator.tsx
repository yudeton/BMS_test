import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';

// 畫面組件
import { DashboardScreen } from '../screens/DashboardScreen';

// 主題
import { useThemeOnly } from '../theme/ThemeProvider';
import { Text } from '../components/common/Text';

/**
 * 根導航參數類型
 */
export type RootTabParamList = {
  Dashboard: undefined;
  History: undefined;
  Settings: undefined;
  Alerts: undefined;
};

export type RootStackParamList = {
  MainTabs: undefined;
  AlertDetail: { alertId: number };
  DeviceSettings: undefined;
};

const Tab = createBottomTabNavigator<RootTabParamList>();
const Stack = createStackNavigator<RootStackParamList>();

/**
 * 底部標籤導航器
 */
const MainTabNavigator: React.FC = () => {
  const theme = useThemeOnly();

  /**
   * 暫時的佔位符畫面組件
   */
  const PlaceholderScreen: React.FC<{ title: string }> = ({ title }) => (
    <div style={{
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: theme.colors.background,
    }}>
      <Text variant="h3">{title}</Text>
      <Text variant="body2" color={theme.colors.textSecondary}>
        此功能正在開發中
      </Text>
    </div>
  );

  return (
    <Tab.Navigator
      screenOptions={{
        tabBarStyle: {
          backgroundColor: theme.colors.surface,
          borderTopColor: theme.colors.border,
          paddingTop: 8,
          paddingBottom: 8,
          height: 70,
        },
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.textSecondary,
        headerShown: false,
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '500',
          marginTop: 4,
        },
      }}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          tabBarLabel: '儀表板',
          tabBarIcon: ({ color, size }) => (
            <Text style={{ color, fontSize: size }}>🏠</Text>
          ),
        }}
      />
      
      <Tab.Screen
        name="History"
        options={{
          tabBarLabel: '歷史',
          tabBarIcon: ({ color, size }) => (
            <Text style={{ color, fontSize: size }}>📊</Text>
          ),
        }}
      >
        {() => <PlaceholderScreen title="歷史數據" />}
      </Tab.Screen>
      
      <Tab.Screen
        name="Alerts"
        options={{
          tabBarLabel: '警報',
          tabBarIcon: ({ color, size }) => (
            <Text style={{ color, fontSize: size }}>🚨</Text>
          ),
        }}
      >
        {() => <PlaceholderScreen title="警報管理" />}
      </Tab.Screen>
      
      <Tab.Screen
        name="Settings"
        options={{
          tabBarLabel: '設定',
          tabBarIcon: ({ color, size }) => (
            <Text style={{ color, fontSize: size }}>⚙️</Text>
          ),
        }}
      >
        {() => <PlaceholderScreen title="設定" />}
      </Tab.Screen>
    </Tab.Navigator>
  );
};

/**
 * 根導航器
 */
export const RootNavigator: React.FC = () => {
  const theme = useThemeOnly();

  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: theme.colors.surface,
          borderBottomColor: theme.colors.border,
        },
        headerTintColor: theme.colors.text,
        headerTitleStyle: {
          fontWeight: '600',
        },
        cardStyle: {
          backgroundColor: theme.colors.background,
        },
      }}
    >
      <Stack.Screen
        name="MainTabs"
        component={MainTabNavigator}
        options={{ headerShown: false }}
      />
      
      {/* 模態畫面可以在這裡添加 */}
      {/*
      <Stack.Screen
        name="AlertDetail"
        component={AlertDetailScreen}
        options={{
          title: '警報詳情',
          presentation: 'modal',
        }}
      />
      */}
    </Stack.Navigator>
  );
};