#!/usr/bin/env python3
"""
正確的 Smart BMS 協議測試
使用 DD A5 協議格式（通用中國 BMS 協議）
"""

import asyncio
import struct
from datetime import datetime
from bleak import BleakClient, BleakScanner

class SmartBMSProtocol:
    def __init__(self, mac_address):
        self.mac = mac_address
        self.client = None
        self.responses = []
        
        # BLE 特徵值
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb"
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
    def calculate_checksum(self, data):
        """計算校驗和"""
        # 校驗和 = 65536 - sum(data)
        checksum = 0x10000 - sum(data)
        return checksum & 0xFFFF
    
    def build_read_command(self, cmd_id):
        """構建讀取命令"""
        # 格式: DD A5 CMD 00 CHECKSUM(2bytes) 77
        packet = bytearray([0xDD, 0xA5, cmd_id, 0x00])
        checksum = self.calculate_checksum(packet)
        packet.extend([(checksum >> 8) & 0xFF, checksum & 0xFF])
        packet.append(0x77)
        return bytes(packet)
    
    def build_write_command(self, register, data):
        """構建寫入命令"""
        # 格式: DD 5A REGISTER LENGTH DATA CHECKSUM 77
        packet = bytearray([0xDD, 0x5A, register, len(data)])
        packet.extend(data)
        checksum = self.calculate_checksum(packet)
        packet.extend([(checksum >> 8) & 0xFF, checksum & 0xFF])
        packet.append(0x77)
        return bytes(packet)
    
    def notification_handler(self, sender, data):
        """處理通知數據"""
        if data:
            self.responses.append(data)
            print(f"📥 收到響應: {data.hex().upper()}")
    
    def parse_basic_info(self, data):
        """解析基本信息（命令03的響應）"""
        if len(data) < 34:
            return None
            
        try:
            # 跳過頭部 DD 03
            idx = 4
            
            # 總電壓 (2 bytes, 10mV)
            voltage = struct.unpack('>H', data[idx:idx+2])[0] / 100.0
            idx += 2
            
            # 電流 (2 bytes, 10mA, signed)
            current_raw = struct.unpack('>h', data[idx:idx+2])[0]
            current = current_raw / 100.0
            idx += 2
            
            # 剩餘容量 (2 bytes, 10mAh)
            remain_cap = struct.unpack('>H', data[idx:idx+2])[0] / 100.0
            idx += 2
            
            # 標稱容量 (2 bytes, 10mAh)
            nominal_cap = struct.unpack('>H', data[idx:idx+2])[0] / 100.0
            idx += 2
            
            # 循環次數 (2 bytes)
            cycles = struct.unpack('>H', data[idx:idx+2])[0]
            idx += 2
            
            # 生產日期 (2 bytes)
            idx += 2
            
            # 平衡狀態 (2 bytes)
            balance = struct.unpack('>H', data[idx:idx+2])[0]
            idx += 2
            
            # 平衡狀態2 (2 bytes)
            idx += 2
            
            # 保護狀態 (2 bytes)
            protect = struct.unpack('>H', data[idx:idx+2])[0]
            idx += 2
            
            # 軟體版本 (1 byte)
            version = data[idx]
            idx += 1
            
            # RSOC (1 byte, %)
            rsoc = data[idx]
            idx += 1
            
            # FET狀態 (1 byte)
            fet = data[idx]
            charge_fet = "開啟" if (fet & 0x01) else "關閉"
            discharge_fet = "開啟" if (fet & 0x02) else "關閉"
            idx += 1
            
            # 電芯數 (1 byte)
            cell_count = data[idx]
            idx += 1
            
            # 溫度數量 (1 byte)
            temp_count = data[idx]
            idx += 1
            
            # 溫度數據
            temps = []
            for i in range(temp_count):
                if idx < len(data) - 2:
                    temp_raw = struct.unpack('>H', data[idx:idx+2])[0]
                    temp = (temp_raw - 2731) / 10.0  # 轉換為攝氏度
                    temps.append(temp)
                    idx += 2
            
            return {
                "電壓": f"{voltage:.2f}V",
                "電流": f"{current:.2f}A",
                "剩餘容量": f"{remain_cap:.2f}Ah",
                "標稱容量": f"{nominal_cap:.2f}Ah",
                "SOC": f"{rsoc}%",
                "循環次數": cycles,
                "充電MOSFET": charge_fet,
                "放電MOSFET": discharge_fet,
                "電芯數": cell_count,
                "溫度": [f"{t:.1f}°C" for t in temps],
                "保護狀態": f"0x{protect:04X}",
                "平衡狀態": f"0x{balance:04X}"
            }
        except Exception as e:
            print(f"解析錯誤: {e}")
            return None
    
    def parse_cell_voltages(self, data):
        """解析電芯電壓（命令04的響應）"""
        if len(data) < 4:
            return None
            
        try:
            cells = []
            idx = 4  # 跳過頭部
            
            while idx < len(data) - 3:  # 留出校驗和空間
                if idx + 1 < len(data):
                    voltage = struct.unpack('>H', data[idx:idx+2])[0] / 1000.0
                    if voltage > 0 and voltage < 5.0:  # 合理的電芯電壓範圍
                        cells.append(voltage)
                    idx += 2
                else:
                    break
                    
            return cells
        except Exception as e:
            print(f"解析電芯電壓錯誤: {e}")
            return None
    
    def parse_hardware_info(self, data):
        """解析硬體信息（命令05的響應）"""
        if len(data) < 4:
            return None
            
        try:
            # 跳過頭部，提取 ASCII 字符串
            idx = 4
            info = []
            
            while idx < len(data) - 3:  # 留出校驗和空間
                char = data[idx]
                if 32 <= char <= 126:  # 可打印 ASCII
                    info.append(chr(char))
                idx += 1
                
            return ''.join(info)
        except Exception as e:
            print(f"解析硬體信息錯誤: {e}")
            return None
    
    async def connect(self):
        """連接 BMS"""
        try:
            print(f"\n🔌 連接到 {self.mac}...")
            
            # 先掃描設備
            device = await BleakScanner.find_device_by_address(self.mac, timeout=5.0)
            if not device:
                print("❌ 找不到設備")
                return False
                
            self.client = BleakClient(self.mac)
            await self.client.connect()
            
            if not self.client.is_connected:
                print("❌ 連接失敗")
                return False
                
            print("✅ 連接成功！")
            
            # 啟用通知
            await self.client.start_notify(self.read_char, self.notification_handler)
            
            return True
            
        except Exception as e:
            print(f"❌ 連接錯誤: {e}")
            return False
    
    async def send_command(self, command, description, wait_time=2):
        """發送命令並等待響應"""
        self.responses.clear()
        
        print(f"\n📤 {description}")
        print(f"   命令: {command.hex().upper()}")
        
        await self.client.write_gatt_char(self.write_char, command, response=False)
        await asyncio.sleep(wait_time)
        
        return self.responses
    
    async def test_protocol(self):
        """測試完整協議"""
        if not await self.connect():
            return
            
        try:
            print("\n" + "="*60)
            print("🔬 開始 Smart BMS 協議測試 (DD A5 格式)")
            print("="*60)
            
            # 1. 讀取基本信息
            cmd = self.build_read_command(0x03)
            responses = await self.send_command(cmd, "讀取基本信息 (03)")
            
            if responses:
                for resp in responses:
                    if resp[0] == 0xDD and len(resp) > 4:
                        info = self.parse_basic_info(resp)
                        if info:
                            print("\n📊 基本信息:")
                            for key, value in info.items():
                                print(f"   {key}: {value}")
            
            # 2. 讀取電芯電壓
            cmd = self.build_read_command(0x04)
            responses = await self.send_command(cmd, "讀取電芯電壓 (04)")
            
            if responses:
                for resp in responses:
                    if resp[0] == 0xDD and len(resp) > 4:
                        cells = self.parse_cell_voltages(resp)
                        if cells:
                            print("\n🔋 電芯電壓:")
                            total = 0
                            for i, v in enumerate(cells, 1):
                                print(f"   電芯 {i}: {v:.3f}V")
                                total += v
                            print(f"   總電壓: {total:.2f}V")
            
            # 3. 讀取硬體信息
            cmd = self.build_read_command(0x05)
            responses = await self.send_command(cmd, "讀取硬體信息 (05)")
            
            if responses:
                for resp in responses:
                    if resp[0] == 0xDD and len(resp) > 4:
                        hw_info = self.parse_hardware_info(resp)
                        if hw_info:
                            print(f"\n💻 硬體信息: {hw_info}")
            
            # 4. 如果 MOSFET 關閉，嘗試開啟
            print("\n" + "="*60)
            print("🔧 檢查 MOSFET 狀態...")
            
            # 發送預備命令
            preamble = bytes.fromhex("DD5A00025678FF3077")
            responses = await self.send_command(preamble, "發送預備命令")
            
            # 嘗試開啟 MOSFET
            mosfet_on = bytes.fromhex("DD5AE1020000FF1D77")
            responses = await self.send_command(mosfet_on, "嘗試開啟 MOSFET")
            
            # 再次讀取基本信息確認狀態
            await asyncio.sleep(1)
            cmd = self.build_read_command(0x03)
            responses = await self.send_command(cmd, "確認 MOSFET 狀態")
            
            if responses:
                for resp in responses:
                    if resp[0] == 0xDD and len(resp) > 4:
                        info = self.parse_basic_info(resp)
                        if info:
                            print(f"\n最終 MOSFET 狀態:")
                            print(f"   充電: {info.get('充電MOSFET', '未知')}")
                            print(f"   放電: {info.get('放電MOSFET', '未知')}")
            
        except Exception as e:
            print(f"\n❌ 測試錯誤: {e}")
            
        finally:
            if self.client:
                await self.client.disconnect()
                print("\n👋 已斷開連接")

async def main():
    # 你的 BMS MAC 地址
    mac = "41:18:12:01:37:71"
    
    tester = SmartBMSProtocol(mac)
    await tester.test_protocol()

if __name__ == "__main__":
    print("🚀 Smart BMS 正確協議測試工具")
    print("使用 DD A5 通用中國 BMS 協議\n")
    asyncio.run(main())