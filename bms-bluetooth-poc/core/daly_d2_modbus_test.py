#!/usr/bin/env python3
"""
DALY BMS D2 Modbus 協議測試工具
針對 K00T 韌體的新版協議
"""

import asyncio
import struct
from datetime import datetime
from bleak import BleakClient, BleakScanner

class DalyD2ModbusProtocol:
    def __init__(self, mac_address):
        self.mac = mac_address
        self.client = None
        self.responses = []
        
        # BLE 特徵值
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb"
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
        # Modbus 設備地址
        self.device_addr = 0xD2
        
        # 已知寄存器地址
        self.registers = {
            "cell_voltage_base": 0x0000,  # 電芯電壓起始地址
            "temperature_base": 0x0020,   # 溫度起始地址  
            "total_voltage": 0x0028,      # 總電壓
            "current": 0x0029,            # 電流
            "fault_bitmap": 0x003A,       # 故障狀態
            "soc": 0x002C,               # SOC (推測)
            "mosfet_status": 0x002D,     # MOSFET 狀態 (推測)
        }
    
    def calculate_modbus_crc16(self, data):
        """標準 Modbus CRC-16 計算"""
        crc = 0xFFFF
        
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc = crc >> 1
        
        return crc
    
    def build_modbus_read_command(self, register_addr, num_registers=1):
        """構建 Modbus 讀取命令 (8 bytes)"""
        # Modbus RTU 格式: [設備地址][功能碼][起始地址H][起始地址L][寄存器數H][寄存器數L][CRC_L][CRC_H]
        packet = [
            self.device_addr,              # 設備地址 (0xD2)
            0x03,                          # 功能碼：讀取保持寄存器
            (register_addr >> 8) & 0xFF,   # 起始地址高位元組
            register_addr & 0xFF,          # 起始地址低位元組
            (num_registers >> 8) & 0xFF,   # 寄存器數量高位元組
            num_registers & 0xFF           # 寄存器數量低位元組
        ]
        
        # 計算 CRC
        crc = self.calculate_modbus_crc16(packet)
        
        # CRC 先低位元組後高位元組 (Modbus 標準)
        packet.extend([crc & 0xFF, (crc >> 8) & 0xFF])
        
        return bytes(packet)
    
    def verify_known_commands(self):
        """驗證已知命令的構建"""
        print("🔬 驗證 D2 Modbus 命令構建:")
        
        # 已知的工作命令範例 (來自研究)
        known_cmd = "d2 03 00 00 00 3e d7 b9"
        known_bytes = bytes.fromhex(known_cmd.replace(" ", ""))
        
        # 嘗試重建這個命令 (讀取從 0x0000 開始的 0x3E=62 個寄存器)
        generated = self.build_modbus_read_command(0x0000, 0x003E)
        
        match = "✅" if known_bytes == generated else "❌"
        print(f"  {match} 大範圍讀取命令:")
        print(f"     已知: {known_cmd.upper()}")
        print(f"     產生: {generated.hex(' ').upper()}")
        
        if known_bytes != generated:
            # 分析差異
            print(f"     差異分析:")
            for i, (exp, gen) in enumerate(zip(known_bytes, generated)):
                if exp != gen:
                    print(f"       位置 {i}: 預期 0x{exp:02X}, 產生 0x{gen:02X}")
        
        # 測試個別寄存器命令
        print(f"\n  個別寄存器命令:")
        for name, addr in self.registers.items():
            if name.endswith("_base"):
                continue
            cmd = self.build_modbus_read_command(addr, 1)
            print(f"     {name}: {cmd.hex(' ').upper()}")
    
    def parse_modbus_response(self, command, response):
        """解析 Modbus 響應"""
        if len(response) < 5:
            return {"error": "響應太短"}
        
        # Modbus 響應格式: [設備地址][功能碼][數據長度][數據...][CRC_L][CRC_H]
        if response[0] != self.device_addr:
            return {"error": f"設備地址不匹配: 期望 0x{self.device_addr:02X}, 收到 0x{response[0]:02X}"}
        
        if response[1] != 0x03:
            if response[1] & 0x80:  # 錯誤響應
                error_code = response[2] if len(response) > 2 else 0
                return {"error": f"Modbus 錯誤: 功能碼 0x{response[1]:02X}, 錯誤碼 0x{error_code:02X}"}
            else:
                return {"error": f"功能碼不匹配: 期望 0x03, 收到 0x{response[1]:02X}"}
        
        data_length = response[2]
        if len(response) < 3 + data_length + 2:
            return {"error": "數據長度不足"}
        
        # 提取數據部分
        data_bytes = response[3:3+data_length]
        
        # 驗證 CRC (可選)
        expected_crc = struct.unpack('<H', response[-2:])[0]  # 小端序
        calculated_crc = self.calculate_modbus_crc16(response[:-2])
        
        crc_valid = expected_crc == calculated_crc
        
        # 解析數據內容
        parsed_data = {
            "raw_data": data_bytes.hex().upper(),
            "data_length": data_length,
            "crc_valid": crc_valid
        }
        
        # 根據請求的寄存器地址解析具體數值
        if len(command) >= 6:
            requested_addr = (command[2] << 8) | command[3]
            num_registers = (command[4] << 8) | command[5]
            
            if requested_addr == self.registers["total_voltage"] and data_length >= 2:
                raw_voltage = struct.unpack('>H', data_bytes[:2])[0]
                parsed_data["total_voltage"] = raw_voltage * 0.1
            
            elif requested_addr == self.registers["current"] and data_length >= 2:
                raw_current = struct.unpack('>H', data_bytes[:2])[0]  # 無符號
                # 電流可能使用偏移編碼，30000為零點
                if raw_current >= 30000:
                    actual_current = (raw_current - 30000) * 0.1  # 放電為正
                    parsed_data["current"] = actual_current
                    parsed_data["current_direction"] = "放電" if actual_current > 0 else "靜止"
                else:
                    actual_current = (30000 - raw_current) * 0.1  # 充電為負
                    parsed_data["current"] = -actual_current
                    parsed_data["current_direction"] = "充電"
                parsed_data["raw_current"] = raw_current
            
            elif requested_addr == self.registers["cell_voltage_base"] and data_length >= 2:
                # 電芯電壓數據
                voltages = []
                for i in range(0, min(data_length, 16), 2):  # 最多8串
                    if i + 1 < len(data_bytes):
                        raw_v = struct.unpack('>H', data_bytes[i:i+2])[0]
                        voltages.append(raw_v * 0.001)
                parsed_data["cell_voltages"] = voltages
            
            elif requested_addr == 0x0000 and num_registers == 0x003E:
                # 大範圍讀取，嘗試解析多種數據
                parsed_data["analysis"] = "大範圍數據包含多種資訊"
                if data_length >= 80:  # 0x3E * 2 = 124 bytes
                    # 嘗試提取總電壓 (地址 0x28 -> 位置 0x28*2 = 80)
                    if 80 < len(data_bytes):
                        voltage_pos = 0x28 * 2
                        if voltage_pos + 1 < len(data_bytes):
                            raw_v = struct.unpack('>H', data_bytes[voltage_pos:voltage_pos+2])[0]
                            parsed_data["extracted_voltage"] = raw_v * 0.1
        
        return parsed_data
    
    def notification_handler(self, sender, data):
        """處理通知數據"""
        if data:
            self.responses.append(data)
            print(f"📥 收到響應: {data.hex(' ').upper()} ({len(data)} bytes)")
    
    async def connect(self):
        """連接 BMS (直接連接，不預掃描)"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                print(f"\n🔌 連接到 {self.mac}... (嘗試 {attempt + 1}/{max_retries})")
                
                # 直接連接，不先掃描
                self.client = BleakClient(self.mac)
                await self.client.connect(timeout=10.0)  # 增加超時時間
                
                if not self.client.is_connected:
                    print("❌ 連接失敗")
                    if attempt < max_retries - 1:
                        print("⏳ 等待 2 秒後重試...")
                        await asyncio.sleep(2)
                        continue
                    return False
                    
                print("✅ 連接成功！")
                
                # 啟用通知
                await self.client.start_notify(self.read_char, self.notification_handler)
                
                return True
                
            except Exception as e:
                print(f"❌ 連接錯誤: {e}")
                if attempt < max_retries - 1:
                    print("⏳ 等待 2 秒後重試...")
                    await asyncio.sleep(2)
                    continue
                    
        return False
    
    async def send_modbus_command(self, command, description, wait_time=3):
        """發送 Modbus 命令並分析響應"""
        self.responses.clear()
        
        print(f"\n📤 {description}")
        print(f"   命令: {command.hex(' ').upper()}")
        
        try:
            await self.client.write_gatt_char(self.write_char, command, response=False)
            await asyncio.sleep(wait_time)
            
            if self.responses:
                for i, resp in enumerate(self.responses, 1):
                    print(f"\n🔍 響應 {i} 分析:")
                    if resp == command:
                        print("   ⚠️  回音響應 - 協議可能仍不正確")
                    else:
                        parsed = self.parse_modbus_response(command, resp)
                        print(f"   ✅ 真實響應！")
                        for key, value in parsed.items():
                            if key == "raw_data":
                                print(f"      原始數據: {value}")
                            elif key == "crc_valid":
                                status = "✅" if value else "❌"
                                print(f"      CRC 驗證: {status}")
                            else:
                                print(f"      {key}: {value}")
            else:
                print("   ❌ 無響應")
                
        except Exception as e:
            print(f"   ❌ 發送錯誤: {e}")
        
        return self.responses
    
    async def comprehensive_test(self):
        """全面 D2 Modbus 測試"""
        if not await self.connect():
            return
            
        try:
            print("\n" + "="*70)
            print("🚀 DALY BMS D2 Modbus 協議測試")
            print("="*70)
            
            # 1. 驗證命令構建
            self.verify_known_commands()
            
            # 2. 測試大範圍讀取 (模仿已知工作命令)
            print(f"\n📋 測試大範圍讀取 (0x0000-0x003E):")
            cmd = self.build_modbus_read_command(0x0000, 0x003E)
            await self.send_modbus_command(cmd, "大範圍數據讀取", wait_time=4)
            
            # 3. 測試個別重要寄存器
            print(f"\n📋 測試個別寄存器:")
            
            # 總電壓
            cmd = self.build_modbus_read_command(self.registers["total_voltage"], 1)
            await self.send_modbus_command(cmd, "讀取總電壓 (0x0028)")
            await asyncio.sleep(0.5)
            
            # 電流
            cmd = self.build_modbus_read_command(self.registers["current"], 1)
            await self.send_modbus_command(cmd, "讀取電流 (0x0029)")
            await asyncio.sleep(0.5)
            
            # 電芯電壓 (讀取 8 個)
            cmd = self.build_modbus_read_command(self.registers["cell_voltage_base"], 8)
            await self.send_modbus_command(cmd, "讀取電芯電壓 (0x0000-0x0007)")
            await asyncio.sleep(0.5)
            
            # 溫度
            cmd = self.build_modbus_read_command(self.registers["temperature_base"], 4)
            await self.send_modbus_command(cmd, "讀取溫度 (0x0020-0x0023)")
            
        except Exception as e:
            print(f"\n❌ 測試錯誤: {e}")
            
        finally:
            if self.client:
                await self.client.disconnect()
                print("\n👋 已斷開連接")

async def main():
    mac = "41:18:12:01:37:71"
    
    tester = DalyD2ModbusProtocol(mac)
    await tester.comprehensive_test()

if __name__ == "__main__":
    print("🔧 DALY BMS D2 Modbus 協議測試工具")
    print("專為 K00T 韌體設計\n")
    asyncio.run(main())