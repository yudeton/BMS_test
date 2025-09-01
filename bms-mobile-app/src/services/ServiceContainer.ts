import 'reflect-metadata';
import { container, injectable, inject, singleton } from 'tsyringe';

// 服務令牌常數
export const SERVICE_TOKENS = {
  BLE_SERVICE: 'IBLEService',
  NOTIFICATION_SERVICE: 'INotificationService',
  STORAGE_SERVICE: 'IStorageService',
  DATA_SERVICE: 'IDataService'
} as const;

/**
 * 服務容器管理類
 * 基於 TSyringe 的依賴注入容器包裝
 */
export class ServiceContainer {
  private static _instance: ServiceContainer;
  private _initialized = false;

  private constructor() {}

  /**
   * 獲取單例實例
   */
  static getInstance(): ServiceContainer {
    if (!ServiceContainer._instance) {
      ServiceContainer._instance = new ServiceContainer();
    }
    return ServiceContainer._instance;
  }

  /**
   * 註冊服務實例
   * @param token 服務令牌
   * @param implementation 服務實現
   */
  register<T>(token: string, implementation: new (...args: any[]) => T): void {
    container.register<T>(token, { useClass: implementation });
  }

  /**
   * 註冊單例服務
   * @param token 服務令牌
   * @param implementation 服務實現
   */
  registerSingleton<T>(token: string, implementation: new (...args: any[]) => T): void {
    container.registerSingleton<T>(token, implementation);
  }

  /**
   * 註冊實例
   * @param token 服務令牌
   * @param instance 服務實例
   */
  registerInstance<T>(token: string, instance: T): void {
    container.registerInstance<T>(token, instance);
  }

  /**
   * 解析服務
   * @param token 服務令牌
   * @returns 服務實例
   */
  resolve<T>(token: string): T {
    return container.resolve<T>(token);
  }

  /**
   * 檢查服務是否已註冊
   * @param token 服務令牌
   * @returns 是否已註冊
   */
  isRegistered(token: string): boolean {
    return container.isRegistered(token);
  }

  /**
   * 清空容器
   */
  clear(): void {
    container.clearInstances();
    this._initialized = false;
  }

  /**
   * 初始化所有服務
   * 這個方法在應用啟動時呼叫
   */
  async initializeServices(): Promise<void> {
    if (this._initialized) {
      return;
    }

    try {
      console.log('🚀 初始化服務容器...');

      // 預先解析所有服務以確保它們正確初始化
      const services = Object.values(SERVICE_TOKENS);
      
      for (const serviceToken of services) {
        if (this.isRegistered(serviceToken)) {
          const service = this.resolve<any>(serviceToken);
          
          // 如果服務有 initialize 方法，呼叫它
          if (service && typeof service.initialize === 'function') {
            console.log(`📦 初始化服務: ${serviceToken}`);
            await service.initialize();
          }
        }
      }

      this._initialized = true;
      console.log('✅ 服務容器初始化完成');

    } catch (error) {
      console.error('❌ 服務容器初始化失敗:', error);
      throw error;
    }
  }

  /**
   * 關閉所有服務
   * 這個方法在應用關閉時呼叫
   */
  async shutdownServices(): Promise<void> {
    if (!this._initialized) {
      return;
    }

    try {
      console.log('🔄 關閉服務容器...');

      const services = Object.values(SERVICE_TOKENS);
      
      for (const serviceToken of services) {
        if (this.isRegistered(serviceToken)) {
          const service = this.resolve<any>(serviceToken);
          
          // 如果服務有 shutdown 方法，呼叫它
          if (service && typeof service.shutdown === 'function') {
            console.log(`📦 關閉服務: ${serviceToken}`);
            await service.shutdown();
          }
        }
      }

      this.clear();
      console.log('✅ 服務容器已關閉');

    } catch (error) {
      console.error('❌ 服務容器關閉失敗:', error);
      throw error;
    }
  }

  /**
   * 獲取初始化狀態
   */
  get initialized(): boolean {
    return this._initialized;
  }
}

/**
 * 服務定位器模式的便利函數
 * 用於在無法使用依賴注入的地方獲取服務
 */
export class ServiceLocator {
  private static container = ServiceContainer.getInstance();

  /**
   * 獲取 BLE 服務
   */
  static getBLEService(): any {
    return ServiceLocator.container.resolve(SERVICE_TOKENS.BLE_SERVICE);
  }

  /**
   * 獲取通知服務
   */
  static getNotificationService(): any {
    return ServiceLocator.container.resolve(SERVICE_TOKENS.NOTIFICATION_SERVICE);
  }

  /**
   * 獲取存儲服務
   */
  static getStorageService(): any {
    return ServiceLocator.container.resolve(SERVICE_TOKENS.STORAGE_SERVICE);
  }

  /**
   * 獲取數據服務
   */
  static getDataService(): any {
    return ServiceLocator.container.resolve(SERVICE_TOKENS.DATA_SERVICE);
  }
}

// 匯出裝飾器以供使用
export { injectable, inject, singleton };

// 匯出預設容器實例
export const serviceContainer = ServiceContainer.getInstance();