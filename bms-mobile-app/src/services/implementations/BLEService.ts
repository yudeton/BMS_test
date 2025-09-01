import { BleManager, Device, BleError, Characteristic, Subscription } from 'react-native-ble-plx';
import { injectable } from 'tsyringe';
import { IBLEService } from '@services/interfaces/IBLEService';
import { BatteryData, BatteryDataBuilder, ConnectionStatus, CurrentDirection } from '@domain/entities/BatteryData';
import { DalyD2ModbusProtocol } from '@utils/BMSProtocol';

/**
 * BLE 服務實作
 * 基於 react-native-ble-plx 實現 DALY BMS 藍牙通訊
 */
@injectable()
export class BLEService implements IBLEService {
  private bleManager: BleManager;
  private protocol: DalyD2ModbusProtocol;
  private connectedDevice: Device | null = null;
  private responseBuffer: Uint8Array[] = [];
  
  // 統計數據
  private readCount = 0;
  private errorCount = 0;
  private lastReadTime: number | null = null;
  
  // 事件監聽器
  private connectionStatusListeners: Array<(status: ConnectionStatus) => void> = [];
  private dataUpdateListeners: Array<(data: BatteryData) => void> = [];
  private notificationSubscription: Subscription | null = null;

  constructor() {
    this.bleManager = new BleManager();
    this.protocol = new DalyD2ModbusProtocol();
    
    // 監聽藍牙狀態變化
    this.setupBleStateMonitoring();
  }

  /**
   * 初始化服務
   */
  async initialize(): Promise<void> {
    try {
      const state = await this.bleManager.state();
      console.log('📱 BLE 狀態:', state);
      
      if (state !== 'PoweredOn') {
        throw new Error('藍牙未開啟或不可用');
      }
    } catch (error) {
      console.error('❌ BLE 服務初始化失敗:', error);
      throw error;
    }
  }

  /**
   * 設置藍牙狀態監控
   */
  private setupBleStateMonitoring(): void {
    this.bleManager.onStateChange((state) => {
      console.log('📡 BLE 狀態變化:', state);
      
      if (state !== 'PoweredOn' && this.connectedDevice) {
        this.handleConnectionLost();
      }
    }, true);
  }

  /**
   * 連接到指定的 BMS 設備
   */
  async connect(macAddress: string): Promise<boolean> {
    try {
      this.notifyConnectionStatus(ConnectionStatus.CONNECTING);
      console.log(`🔌 連接到 BMS: ${macAddress}`);

      // 如果已連接到其他設備，先斷開
      if (this.connectedDevice) {
        await this.disconnect();
      }

      // 掃描並連接設備
      const device = await this.scanAndConnect(macAddress);
      
      if (!device) {
        throw new Error('無法找到或連接到指定設備');
      }

      this.connectedDevice = device;

      // 發現服務和特徵值
      await this.discoverServicesAndCharacteristics();

      // 啟用通知
      await this.enableNotifications();

      this.notifyConnectionStatus(ConnectionStatus.CONNECTED);
      console.log('✅ BMS 連接成功');
      
      return true;

    } catch (error) {
      console.error('❌ BMS 連接失敗:', error);
      this.errorCount++;
      this.notifyConnectionStatus(ConnectionStatus.ERROR);
      return false;
    }
  }

  /**
   * 掃描並連接設備
   */
  private async scanAndConnect(macAddress: string): Promise<Device | null> {
    const maxRetries = 3;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        console.log(`🔍 掃描設備... (嘗試 ${attempt}/${maxRetries})`);

        // 直接嘗試連接（如果設備已知）
        let device: Device;
        try {
          device = await this.bleManager.connectToDevice(macAddress, {
            timeout: 10000,
            refreshGatt: 'OnConnected'
          });
          
          if (device.isConnected) {
            console.log('✅ 直接連接成功');
            return device;
          }
        } catch (directConnectError) {
          console.log('⚠️ 直接連接失敗，開始掃描...');
        }

        // 掃描設備
        const scannedDevice = await this.scanForDevice(macAddress);
        if (scannedDevice) {
          const connectedDevice = await scannedDevice.connect({
            timeout: 10000,
            refreshGatt: 'OnConnected'
          });
          
          console.log('✅ 掃描後連接成功');
          return connectedDevice;
        }

        if (attempt < maxRetries) {
          console.log('⏳ 等待 2 秒後重試...');
          await this.delay(2000);
        }

      } catch (error) {
        console.error(`❌ 連接嘗試 ${attempt} 失敗:`, error);
        
        if (attempt < maxRetries) {
          await this.delay(2000);
        }
      }
    }

    return null;
  }

  /**
   * 掃描特定設備
   */
  private async scanForDevice(macAddress: string): Promise<Device | null> {
    return new Promise((resolve) => {
      let found = false;
      const timeoutId = setTimeout(() => {
        if (!found) {
          this.bleManager.stopDeviceScan();
          resolve(null);
        }
      }, 15000);

      this.bleManager.startDeviceScan(null, null, (error, device) => {
        if (error) {
          console.error('掃描錯誤:', error);
          return;
        }

        if (device && device.id.toLowerCase() === macAddress.toLowerCase()) {
          found = true;
          clearTimeout(timeoutId);
          this.bleManager.stopDeviceScan();
          console.log(`📡 找到設備: ${device.name || '未知'} (${device.id})`);
          resolve(device);
        }
      });
    });
  }

  /**
   * 發現服務和特徵值
   */
  private async discoverServicesAndCharacteristics(): Promise<void> {
    if (!this.connectedDevice) {
      throw new Error('設備未連接');
    }

    console.log('🔍 發現服務和特徵值...');
    await this.connectedDevice.discoverAllServicesAndCharacteristics();
    
    // 驗證所需的特徵值存在
    const services = await this.connectedDevice.services();
    console.log('📋 發現服務數量:', services.length);
    
    let hasRequiredCharacteristics = false;
    for (const service of services) {
      const characteristics = await service.characteristics();
      for (const char of characteristics) {
        if (char.uuid === this.protocol.writeCharacteristic || 
            char.uuid === this.protocol.readCharacteristic) {
          hasRequiredCharacteristics = true;
          console.log(`✅ 找到特徵值: ${char.uuid}`);
        }
      }
    }

    if (!hasRequiredCharacteristics) {
      throw new Error('設備不支援所需的特徵值');
    }
  }

  /**
   * 啟用通知
   */
  private async enableNotifications(): Promise<void> {
    if (!this.connectedDevice) {
      throw new Error('設備未連接');
    }

    console.log('🔔 啟用通知...');
    
    this.notificationSubscription = this.connectedDevice.monitorCharacteristicForService(
      null, // 自動發現服務
      this.protocol.readCharacteristic,
      (error, characteristic) => {
        if (error) {
          console.error('通知錯誤:', error);
          return;
        }

        if (characteristic && characteristic.value) {
          this.handleNotification(characteristic);
        }
      }
    );
  }

  /**
   * 處理 BLE 通知數據
   */
  private handleNotification(characteristic: Characteristic): void {
    if (!characteristic.value) return;

    try {
      // 將 Base64 轉換為 Uint8Array
      const data = new Uint8Array(
        atob(characteristic.value)
          .split('')
          .map(char => char.charCodeAt(0))
      );

      this.responseBuffer.push(data);
      
      console.log(
        '📥 收到響應:',
        Array.from(data).map(b => b.toString(16).padStart(2, '0')).join(' ').toUpperCase(),
        `(${data.length} bytes)`
      );

    } catch (error) {
      console.error('❌ 處理通知數據錯誤:', error);
    }
  }

  /**
   * 斷開與 BMS 設備的連接
   */
  async disconnect(): Promise<void> {
    try {
      if (this.notificationSubscription) {
        this.notificationSubscription.remove();
        this.notificationSubscription = null;
      }

      if (this.connectedDevice) {
        await this.connectedDevice.cancelConnection();
        this.connectedDevice = null;
      }

      this.notifyConnectionStatus(ConnectionStatus.DISCONNECTED);
      console.log('👋 BMS 已斷開連接');

    } catch (error) {
      console.error('❌ 斷開連接錯誤:', error);
    }
  }

  /**
   * 檢查當前連接狀態
   */
  isConnected(): boolean {
    return this.connectedDevice?.isConnected || false;
  }

  /**
   * 讀取 BMS 數據
   */
  async readBMSData(): Promise<BatteryData | null> {
    if (!this.isConnected()) {
      console.warn('⚠️ BMS 未連接');
      return null;
    }

    try {
      // 清空響應緩衝區
      this.responseBuffer = [];

      // 使用大範圍讀取策略（基於 POC 成功經驗）
      console.log('📤 發送大範圍讀取命令...');
      const command = this.protocol.buildModbusReadCommand(0x0000, 0x003E);
      
      const success = await this.sendCommand(command, 4000);
      if (!success) {
        throw new Error('發送命令失敗');
      }

      // 解析響應
      const batteryData = await this.parseResponses(command);
      if (batteryData) {
        this.readCount++;
        this.lastReadTime = Date.now();
        
        // 通知數據更新監聽器
        this.dataUpdateListeners.forEach(listener => listener(batteryData));
        
        console.log(`✅ BMS 數據讀取成功: ${batteryData.totalVoltage}V, ${batteryData.current}A`);
        return batteryData;
      }

      throw new Error('無法解析 BMS 數據');

    } catch (error) {
      console.error('❌ 讀取 BMS 數據錯誤:', error);
      this.errorCount++;
      return null;
    }
  }

  /**
   * 發送命令到 BMS
   */
  private async sendCommand(command: Uint8Array, timeout: number = 3000): Promise<boolean> {
    if (!this.connectedDevice) {
      throw new Error('設備未連接');
    }

    try {
      // 轉換為 Base64
      const base64Data = btoa(String.fromCharCode(...command));
      
      console.log('📤 發送命令:', this.protocol.commandToHexString(command));
      
      await this.connectedDevice.writeCharacteristicWithResponseForService(
        null, // 自動發現服務
        this.protocol.writeCharacteristic,
        base64Data
      );

      // 等待響應
      await this.delay(timeout);
      return true;

    } catch (error) {
      console.error('❌ 發送命令錯誤:', error);
      return false;
    }
  }

  /**
   * 解析響應數據為電池數據
   */
  private async parseResponses(command: Uint8Array): Promise<BatteryData | null> {
    if (this.responseBuffer.length === 0) {
      console.warn('⚠️ 無響應數據');
      return null;
    }

    for (const response of this.responseBuffer) {
      // 跳過回音響應
      if (this.arraysEqual(response, command)) {
        console.log('⚠️ 跳過回音響應');
        continue;
      }

      // 解析 Modbus 響應
      const parsed = this.protocol.parseModbusResponse(command, response);
      
      if (parsed.isValid && parsed.crcValid && parsed.parsedData) {
        return this.convertToBatteryData(parsed.parsedData);
      }
    }

    return null;
  }

  /**
   * 轉換解析數據為電池數據格式
   */
  private convertToBatteryData(parsedData: Record<string, any>): BatteryData {
    const builder = new BatteryDataBuilder()
      .withConnectionStatus(ConnectionStatus.CONNECTED);

    // 提取電壓
    if (parsedData.extractedVoltage || parsedData.totalVoltage) {
      builder.withVoltage(parsedData.extractedVoltage || parsedData.totalVoltage);
    }

    // 提取電流
    if (parsedData.extractedCurrent !== undefined || parsedData.current !== undefined) {
      const current = parsedData.extractedCurrent !== undefined ? 
        parsedData.extractedCurrent : parsedData.current;
      
      let direction = CurrentDirection.IDLE;
      if (parsedData.extractedCurrentDirection || parsedData.currentDirection) {
        const dir = parsedData.extractedCurrentDirection || parsedData.currentDirection;
        direction = dir === '充電' ? CurrentDirection.CHARGING :
                   dir === '放電' ? CurrentDirection.DISCHARGING :
                   CurrentDirection.IDLE;
      }
      
      builder.withCurrent(current, direction);
    }

    // 提取電芯電壓
    if (parsedData.extractedCellVoltages || parsedData.cellVoltages) {
      builder.withCells(parsedData.extractedCellVoltages || parsedData.cellVoltages);
    }

    // 提取溫度
    if (parsedData.extractedTemperatures || parsedData.temperatures) {
      builder.withTemperatures(parsedData.extractedTemperatures || parsedData.temperatures);
    }

    // 提取 SOC
    if (parsedData.soc !== undefined) {
      builder.withSOC(parsedData.soc);
    } else if (parsedData.extractedVoltage || parsedData.totalVoltage) {
      // 使用電壓估算 SOC
      const voltage = parsedData.extractedVoltage || parsedData.totalVoltage;
      const estimatedSOC = this.estimateSOCFromVoltage(voltage);
      builder.withSOC(estimatedSOC);
    }

    // 設置數據品質
    builder.withQuality({
      source: 'ble',
      crcValid: true,
      signalStrength: -50, // TODO: 獲取實際 RSSI
      completenessScore: 95
    });

    return builder.build();
  }

  /**
   * 基於電壓估算 SOC（8S LiFePO4）
   */
  private estimateSOCFromVoltage(voltage: number): number {
    const minVoltage = 24.0;
    const maxVoltage = 29.2;
    
    if (voltage <= minVoltage) return 0.0;
    if (voltage >= maxVoltage) return 100.0;
    
    const soc = ((voltage - minVoltage) / (maxVoltage - minVoltage)) * 100;
    return Math.round(soc * 10) / 10; // 保留一位小數
  }

  /**
   * 喚醒 BMS
   */
  async wakeBMS(): Promise<void> {
    if (!this.isConnected()) {
      throw new Error('BMS 未連接');
    }

    try {
      console.log('⏰ 喚醒 BMS...');
      const wakeCommand = this.protocol.buildModbusReadCommand(
        this.protocol.registers.totalVoltage, 
        1
      );
      
      await this.sendCommand(wakeCommand, 1000);
      console.log('✅ BMS 喚醒命令已發送');

    } catch (error) {
      console.error('❌ 喚醒 BMS 錯誤:', error);
      throw error;
    }
  }

  /**
   * 獲取連接統計資訊
   */
  getConnectionStats() {
    return {
      connected: this.isConnected(),
      macAddress: this.connectedDevice?.id || null,
      readCount: this.readCount,
      errorCount: this.errorCount,
      lastReadTime: this.lastReadTime,
      successRate: this.readCount + this.errorCount > 0 
        ? (this.readCount / (this.readCount + this.errorCount)) * 100 
        : 0
    };
  }

  /**
   * 註冊連接狀態變化監聽器
   */
  onConnectionStatusChange(callback: (status: ConnectionStatus) => void): void {
    this.connectionStatusListeners.push(callback);
  }

  /**
   * 註冊數據更新監聽器
   */
  onDataUpdate(callback: (data: BatteryData) => void): void {
    this.dataUpdateListeners.push(callback);
  }

  /**
   * 取消所有監聽器
   */
  removeAllListeners(): void {
    this.connectionStatusListeners = [];
    this.dataUpdateListeners = [];
  }

  /**
   * 關閉服務
   */
  async shutdown(): Promise<void> {
    await this.disconnect();
    this.removeAllListeners();
    this.bleManager.destroy();
  }

  // 私有工具方法

  private notifyConnectionStatus(status: ConnectionStatus): void {
    this.connectionStatusListeners.forEach(listener => listener(status));
  }

  private handleConnectionLost(): void {
    this.connectedDevice = null;
    this.notifyConnectionStatus(ConnectionStatus.DISCONNECTED);
    console.log('⚠️ BMS 連接中斷');
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private arraysEqual(a: Uint8Array, b: Uint8Array): boolean {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
      if (a[i] !== b[i]) return false;
    }
    return true;
  }
}