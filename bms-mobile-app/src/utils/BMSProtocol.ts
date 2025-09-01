/**
 * DALY BMS D2 Modbus 協議實作
 * 移植自 Python 版本，專為 K00T 韌體設計
 */

/**
 * BMS 寄存器地址映射
 */
export interface BMSRegisters {
  /** 電芯電壓起始地址 */
  cellVoltageBase: number;
  /** 溫度起始地址 */
  temperatureBase: number;
  /** 總電壓 */
  totalVoltage: number;
  /** 電流 */
  current: number;
  /** SOC（電量百分比） */
  soc: number;
  /** MOSFET 狀態 */
  mosfetStatus: number;
  /** 故障狀態 */
  faultBitmap: number;
}

/**
 * Modbus 響應解析結果
 */
export interface ModbusResponse {
  /** 是否為有效響應 */
  isValid: boolean;
  /** 錯誤訊息（如果有） */
  error?: string;
  /** 原始數據（十六進制字串） */
  rawData?: string;
  /** 數據長度 */
  dataLength?: number;
  /** CRC 驗證狀態 */
  crcValid?: boolean;
  /** 解析後的具體數據 */
  parsedData?: Record<string, any>;
}

/**
 * DALY BMS D2 Modbus 協議類
 */
export class DalyD2ModbusProtocol {
  /** 設備地址 */
  public readonly deviceAddress: number = 0xD2;

  /** BLE 寫入特徵值 UUID */
  public readonly writeCharacteristic: string = '0000fff2-0000-1000-8000-00805f9b34fb';

  /** BLE 讀取特徵值 UUID */
  public readonly readCharacteristic: string = '0000fff1-0000-1000-8000-00805f9b34fb';

  /** 寄存器地址映射 */
  public readonly registers: BMSRegisters;

  constructor(socRegister: number = 0x002C) {
    this.registers = {
      cellVoltageBase: 0x0000,
      temperatureBase: 0x0020,
      totalVoltage: 0x0028,
      current: 0x0029,
      soc: socRegister,
      mosfetStatus: 0x002D,
      faultBitmap: 0x003A
    };
  }

  /**
   * 計算標準 Modbus CRC-16 校驗碼
   * @param data 數據位元組陣列
   * @returns CRC-16 值
   */
  calculateModbusCRC16(data: Uint8Array): number {
    let crc = 0xFFFF;

    for (const byte of data) {
      crc ^= byte;
      for (let i = 0; i < 8; i++) {
        if (crc & 0x0001) {
          crc = (crc >> 1) ^ 0xA001;
        } else {
          crc = crc >> 1;
        }
      }
    }

    return crc & 0xFFFF;
  }

  /**
   * 構建 Modbus 讀取命令
   * @param registerAddress 寄存器地址
   * @param numRegisters 寄存器數量
   * @returns 命令位元組陣列
   */
  buildModbusReadCommand(registerAddress: number, numRegisters: number = 1): Uint8Array {
    // Modbus RTU 格式: [設備地址][功能碼][起始地址H][起始地址L][寄存器數H][寄存器數L][CRC_L][CRC_H]
    const packet = new Uint8Array([
      this.deviceAddress,              // 設備地址 (0xD2)
      0x03,                           // 功能碼：讀取保持寄存器
      (registerAddress >> 8) & 0xFF,  // 起始地址高位元組
      registerAddress & 0xFF,          // 起始地址低位元組
      (numRegisters >> 8) & 0xFF,     // 寄存器數量高位元組
      numRegisters & 0xFF             // 寄存器數量低位元組
    ]);

    // 計算 CRC
    const crc = this.calculateModbusCRC16(packet);
    
    // 建立完整命令（包含 CRC）
    const command = new Uint8Array(packet.length + 2);
    command.set(packet);
    command[packet.length] = crc & 0xFF;           // CRC 低位元組
    command[packet.length + 1] = (crc >> 8) & 0xFF; // CRC 高位元組

    return command;
  }

  /**
   * 解析 Modbus 響應
   * @param command 原始命令
   * @param response 響應數據
   * @returns 解析結果
   */
  parseModbusResponse(command: Uint8Array, response: Uint8Array): ModbusResponse {
    if (response.length < 5) {
      return { isValid: false, error: '響應太短' };
    }

    // 檢查設備地址
    if (response[0] !== this.deviceAddress) {
      return {
        isValid: false,
        error: `設備地址不匹配: 期望 0x${this.deviceAddress.toString(16).toUpperCase()}, 收到 0x${response[0].toString(16).toUpperCase()}`
      };
    }

    // 檢查功能碼
    if (response[1] !== 0x03) {
      if (response[1] & 0x80) { // 錯誤響應
        const errorCode = response.length > 2 ? response[2] : 0;
        return {
          isValid: false,
          error: `Modbus 錯誤: 功能碼 0x${response[1].toString(16).toUpperCase()}, 錯誤碼 0x${errorCode.toString(16).toUpperCase()}`
        };
      } else {
        return {
          isValid: false,
          error: `功能碼不匹配: 期望 0x03, 收到 0x${response[1].toString(16).toUpperCase()}`
        };
      }
    }

    const dataLength = response[2];
    if (response.length < 3 + dataLength + 2) {
      return { isValid: false, error: '數據長度不足' };
    }

    // 提取數據部分
    const dataBytes = response.slice(3, 3 + dataLength);

    // 驗證 CRC（小端序）
    const expectedCRC = response[response.length - 2] | (response[response.length - 1] << 8);
    const calculatedCRC = this.calculateModbusCRC16(response.slice(0, -2));
    const crcValid = expectedCRC === calculatedCRC;

    const result: ModbusResponse = {
      isValid: true,
      rawData: Array.from(dataBytes).map(b => b.toString(16).padStart(2, '0')).join('').toUpperCase(),
      dataLength,
      crcValid
    };

    // 根據命令解析具體數據
    if (command.length >= 6) {
      const requestedAddress = (command[2] << 8) | command[3];
      const numRegisters = (command[4] << 8) | command[5];
      
      result.parsedData = this.parseRegisterData(requestedAddress, numRegisters, dataBytes);
    }

    return result;
  }

  /**
   * 解析特定寄存器的數據
   * @param registerAddress 寄存器地址
   * @param numRegisters 寄存器數量
   * @param data 數據位元組陣列
   * @returns 解析後的數據
   */
  private parseRegisterData(registerAddress: number, numRegisters: number, data: Uint8Array): Record<string, any> {
    const result: Record<string, any> = {};

    try {
      // 總電壓解析
      if (registerAddress === this.registers.totalVoltage && data.length >= 2) {
        const rawVoltage = (data[0] << 8) | data[1];
        result.totalVoltage = rawVoltage * 0.1;
      }

      // 電流解析（含偏移編碼）
      else if (registerAddress === this.registers.current && data.length >= 2) {
        const rawCurrent = (data[0] << 8) | data[1];
        // 電流偏移編碼處理：30000 為零點
        if (rawCurrent >= 30000) {
          const actualCurrent = (rawCurrent - 30000) * 0.1;
          result.current = actualCurrent;
          result.currentDirection = actualCurrent > 0 ? '放電' : '靜止';
        } else {
          const actualCurrent = (30000 - rawCurrent) * 0.1;
          result.current = -actualCurrent;
          result.currentDirection = '充電';
        }
        result.rawCurrent = rawCurrent;
      }

      // 電芯電壓解析
      else if (registerAddress === this.registers.cellVoltageBase) {
        const voltages: number[] = [];
        for (let i = 0; i < Math.min(data.length, numRegisters * 2); i += 2) {
          if (i + 1 < data.length) {
            const rawVoltage = (data[i] << 8) | data[i + 1];
            if (rawVoltage > 0) { // 有效電壓
              voltages.push(rawVoltage * 0.001); // mV 轉 V
            }
          }
        }
        result.cellVoltages = voltages;
      }

      // 溫度解析
      else if (registerAddress === this.registers.temperatureBase) {
        const temperatures: number[] = [];
        for (let i = 0; i < Math.min(data.length, numRegisters * 2); i += 2) {
          if (i + 1 < data.length) {
            const rawTemp = (data[i] << 8) | data[i + 1];
            // 0.1K 轉攝氏度
            const tempC = (rawTemp / 10.0) - 273.1;
            if (tempC >= -40.0 && tempC <= 120.0) { // 有效溫度範圍
              temperatures.push(tempC);
            }
          }
        }
        result.temperatures = temperatures;
      }

      // SOC 解析
      else if (registerAddress === this.registers.soc && data.length >= 2) {
        const rawSOC = (data[0] << 8) | data[1];
        result.soc = rawSOC * 0.1;
      }

      // 大範圍讀取解析（0x0000 開始）
      else if (registerAddress === 0x0000 && numRegisters >= 0x003E) {
        result.analysis = '大範圍數據包含多種資訊';
        
        // 提取總電壓（地址 0x28 -> 位置 0x28*2）
        const voltagePos = this.registers.totalVoltage * 2;
        if (voltagePos + 1 < data.length) {
          const rawVoltage = (data[voltagePos] << 8) | data[voltagePos + 1];
          if (rawVoltage > 0) {
            result.extractedVoltage = rawVoltage * 0.1;
          }
        }

        // 提取電流（地址 0x29 -> 位置 0x29*2）
        const currentPos = this.registers.current * 2;
        if (currentPos + 1 < data.length) {
          const rawCurrent = (data[currentPos] << 8) | data[currentPos + 1];
          if (rawCurrent >= 30000) {
            const actualCurrent = (rawCurrent - 30000) * 0.1;
            result.extractedCurrent = actualCurrent;
            result.extractedCurrentDirection = actualCurrent > 0 ? '放電' : '靜止';
          } else {
            const actualCurrent = (30000 - rawCurrent) * 0.1;
            result.extractedCurrent = -actualCurrent;
            result.extractedCurrentDirection = '充電';
          }
        }

        // 提取電芯電壓（地址 0x0000 開始）
        const cellVoltages: number[] = [];
        for (let i = 0; i < 16; i += 2) { // 8串電池 = 16 位元組
          if (i + 1 < data.length) {
            const rawVoltage = (data[i] << 8) | data[i + 1];
            if (rawVoltage > 0) {
              cellVoltages.push(rawVoltage * 0.001);
            }
          }
        }
        if (cellVoltages.length > 0) {
          result.extractedCellVoltages = cellVoltages;
        }

        // 提取溫度（地址 0x20 開始）
        const tempPos = this.registers.temperatureBase * 2;
        const temperatures: number[] = [];
        for (let i = 0; i < 8; i += 2) { // 4個溫度感測器 = 8 位元組
          const pos = tempPos + i;
          if (pos + 1 < data.length) {
            const rawTemp = (data[pos] << 8) | data[pos + 1];
            const tempC = (rawTemp / 10.0) - 273.1;
            if (tempC >= -40.0 && tempC <= 120.0) {
              temperatures.push(tempC);
            }
          }
        }
        if (temperatures.length > 0) {
          result.extractedTemperatures = temperatures;
        }
      }

    } catch (error) {
      result.parseError = error instanceof Error ? error.message : String(error);
    }

    return result;
  }

  /**
   * 將命令轉換為十六進制字串（用於調試）
   * @param command 命令位元組陣列
   * @returns 十六進制字串
   */
  commandToHexString(command: Uint8Array): string {
    return Array.from(command)
      .map(byte => byte.toString(16).padStart(2, '0'))
      .join(' ')
      .toUpperCase();
  }

  /**
   * 驗證已知命令的構建
   * @returns 驗證結果
   */
  verifyKnownCommands(): { command: string; expected: string; match: boolean }[] {
    const results = [];

    // 已知的大範圍讀取命令
    const knownCommand = 'D2 03 00 00 00 3E D7 B9';
    const generated = this.buildModbusReadCommand(0x0000, 0x003E);
    const generatedHex = this.commandToHexString(generated);

    results.push({
      command: '大範圍讀取 (0x0000-0x003E)',
      expected: knownCommand,
      match: knownCommand === generatedHex
    });

    return results;
  }
}