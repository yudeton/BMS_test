import { ServiceContainer, SERVICE_TOKENS } from './ServiceContainer';

// 服務介面
import { IBLEService } from './interfaces/IBLEService';
import { INotificationService } from './interfaces/INotificationService';
import { IStorageService } from './interfaces/IStorageService';
import { IDataService } from './interfaces/IDataService';

// 服務實作
import { BLEService } from './implementations/BLEService';
import { NotificationService } from './implementations/NotificationService';
import { StorageService } from './implementations/StorageService';
import { DataService } from './implementations/DataService';

/**
 * 服務註冊器
 * 負責註冊所有服務到依賴注入容器
 */
export class ServiceRegistry {
  private static registered = false;

  /**
   * 註冊所有服務
   */
  static registerServices(): void {
    if (ServiceRegistry.registered) {
      console.log('⚠️ 服務已註冊，跳過重複註冊');
      return;
    }

    const container = ServiceContainer.getInstance();

    try {
      console.log('📦 開始註冊服務...');

      // 註冊 BLE 服務（單例）
      container.registerSingleton<IBLEService>(SERVICE_TOKENS.BLE_SERVICE, BLEService);
      console.log('✅ BLE 服務已註冊');

      // 註冊通知服務（單例）
      container.registerSingleton<INotificationService>(SERVICE_TOKENS.NOTIFICATION_SERVICE, NotificationService);
      console.log('✅ 通知服務已註冊');

      // 註冊存儲服務（單例）
      container.registerSingleton<IStorageService>(SERVICE_TOKENS.STORAGE_SERVICE, StorageService);
      console.log('✅ 存儲服務已註冊');

      // 註冊數據服務（單例）
      container.registerSingleton<IDataService>(SERVICE_TOKENS.DATA_SERVICE, DataService);
      console.log('✅ 數據服務已註冊');

      ServiceRegistry.registered = true;
      console.log('🎉 所有服務註冊完成');

    } catch (error) {
      console.error('❌ 服務註冊失敗:', error);
      throw error;
    }
  }

  /**
   * 驗證服務註冊狀態
   */
  static validateServices(): boolean {
    const container = ServiceContainer.getInstance();
    const requiredServices = Object.values(SERVICE_TOKENS);
    
    console.log('🔍 驗證服務註冊狀態...');
    
    for (const serviceToken of requiredServices) {
      if (!container.isRegistered(serviceToken)) {
        console.error(`❌ 服務未註冊: ${serviceToken}`);
        return false;
      } else {
        console.log(`✅ 服務已註冊: ${serviceToken}`);
      }
    }
    
    console.log('✅ 所有必要服務都已註冊');
    return true;
  }

  /**
   * 獲取服務實例（便利方法）
   */
  static getServices() {
    const container = ServiceContainer.getInstance();
    
    return {
      bleService: container.resolve<IBLEService>(SERVICE_TOKENS.BLE_SERVICE),
      notificationService: container.resolve<INotificationService>(SERVICE_TOKENS.NOTIFICATION_SERVICE),
      storageService: container.resolve<IStorageService>(SERVICE_TOKENS.STORAGE_SERVICE),
      dataService: container.resolve<IDataService>(SERVICE_TOKENS.DATA_SERVICE)
    };
  }

  /**
   * 重置註冊狀態（測試用）
   */
  static reset(): void {
    ServiceRegistry.registered = false;
    console.log('🔄 服務註冊狀態已重置');
  }
}

/**
 * 應用啟動時的服務初始化
 */
export async function initializeServices(): Promise<void> {
  try {
    console.log('🚀 開始初始化應用服務...');

    // 註冊服務
    ServiceRegistry.registerServices();

    // 驗證註冊
    const isValid = ServiceRegistry.validateServices();
    if (!isValid) {
      throw new Error('服務註冊驗證失敗');
    }

    // 初始化服務容器
    const container = ServiceContainer.getInstance();
    await container.initializeServices();

    console.log('✅ 應用服務初始化完成');

  } catch (error) {
    console.error('❌ 應用服務初始化失敗:', error);
    throw error;
  }
}

/**
 * 應用關閉時的服務清理
 */
export async function shutdownServices(): Promise<void> {
  try {
    console.log('🔄 開始關閉應用服務...');

    const container = ServiceContainer.getInstance();
    await container.shutdownServices();

    ServiceRegistry.reset();
    
    console.log('✅ 應用服務關閉完成');

  } catch (error) {
    console.error('❌ 應用服務關閉失敗:', error);
  }
}