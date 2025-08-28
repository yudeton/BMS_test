#!/usr/bin/env python3
"""
修正的 Smart BMS 協議測試
使用正確的校驗和算法
"""

import asyncio
import struct
from datetime import datetime
from bleak import BleakClient, BleakScanner

class CorrectSmartBMSProtocol:
    def __init__(self, mac_address):
        self.mac = mac_address
        self.client = None
        self.responses = []
        
        # BLE 特徵值
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb"
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
    def calculate_checksum_correct(self, data):
        """正確的校驗和計算方法"""
        # 校驗和計算範圍：從位置2開始到倒數第3個位元組
        # 即不包含 DD (pos 0), A5 (pos 1), 校驗和 (最後2個), 和 77 (最後1個)
        checksum_data = data[2:]  # 從第3個位元組開始
        
        # 計算：0x10000 - sum(data)
        crc = 0x10000
        for byte_val in checksum_data:
            crc = crc - byte_val
            
        # 確保結果是16位
        crc = crc & 0xFFFF
        
        return crc
    
    def build_read_command_correct(self, cmd_id):
        """使用正確校驗和構建讀取命令"""
        # 基本包結構: DD A5 CMD 00 (數據部分)
        base_packet = [0xDD, 0xA5, cmd_id, 0x00]
        
        # 計算校驗和 (只對 CMD 00 部分)
        checksum_data = [cmd_id, 0x00]
        crc = 0x10000
        for byte_val in checksum_data:
            crc = crc - byte_val
        crc = crc & 0xFFFF
        
        # 構建完整包: DD A5 CMD 00 CHK_H CHK_L 77
        packet = base_packet + [(crc >> 8) & 0xFF, crc & 0xFF, 0x77]
        
        return bytes(packet)
    
    def build_write_command_correct(self, register, data):
        """使用正確校驗和構建寫入命令"""
        base_packet = [0xDD, 0x5A, register, len(data)] + list(data)
        
        # 計算校驗和 (從 register 開始)
        checksum_data = base_packet[2:]
        crc = 0x10000
        for byte_val in checksum_data:
            crc = crc - byte_val
        crc = crc & 0xFFFF
        
        packet = base_packet + [(crc >> 8) & 0xFF, crc & 0xFF, 0x77]
        return bytes(packet)
    
    def verify_known_commands(self):
        """驗證已知命令的校驗和"""
        print("🔬 驗證已知命令校驗和:")
        
        known_commands = {
            "讀取基本信息": ("DD A5 03 00 FF FD 77", 0x03),
            "讀取電芯電壓": ("DD A5 04 00 FF FC 77", 0x04),
            "讀取硬體信息": ("DD A5 05 00 FF FB 77", 0x05),
        }
        
        for desc, (expected_hex, cmd_id) in known_commands.items():
            # 移除空格並轉換為位元組
            expected_bytes = bytes.fromhex(expected_hex.replace(" ", ""))
            generated = self.build_read_command_correct(cmd_id)
            
            match = "✅" if expected_bytes == generated else "❌"
            print(f"  {match} {desc}:")
            print(f"     預期: {expected_hex}")
            print(f"     產生: {generated.hex().upper()}")
            
            if expected_bytes != generated:
                print(f"     差異: 預期校驗和 {expected_bytes[4:6].hex().upper()}, 產生 {generated[4:6].hex().upper()}")
    
    def notification_handler(self, sender, data):
        """處理通知數據"""
        if data:
            self.responses.append(data)
            print(f"📥 收到響應: {data.hex().upper()} ({len(data)} bytes)")
            
            # 詳細分析響應
            if len(data) >= 4:
                if data[0] == 0xDD:
                    if data[1] == 0x03:  # 基本信息響應
                        data_length = data[3]
                        print(f"     基本信息響應，數據長度: {data_length}")
                    elif data[1] == 0x04:  # 電芯電壓響應
                        data_length = data[3]
                        print(f"     電芯電壓響應，數據長度: {data_length}")
                    elif data[1] == 0x05:  # 硬體信息響應
                        data_length = data[3]
                        print(f"     硬體信息響應，數據長度: {data_length}")
                else:
                    print(f"     不是標準 DD 響應格式")
    
    def detailed_response_analysis(self, command_sent, responses):
        """詳細分析響應"""
        print(f"\n🔍 詳細響應分析:")
        print(f"   發送命令: {command_sent.hex().upper()}")
        
        if not responses:
            print("   ❌ 無響應")
            return
            
        for i, resp in enumerate(responses, 1):
            print(f"   響應 {i}: {resp.hex().upper()}")
            
            # 檢查是否為回音
            if resp == command_sent:
                print(f"     ⚠️  完全回音 - BMS 可能在等待正確格式")
            elif resp.startswith(command_sent[:4]):
                print(f"     ⚠️  部分回音 - 可能協議錯誤")
            elif resp[0] == 0xDD and len(resp) > 4:
                print(f"     ✅ 看起來像真實響應!")
                data_length = resp[3] if len(resp) > 3 else 0
                print(f"        數據長度: {data_length}")
                if data_length > 0 and len(resp) > 4 + data_length:
                    data_section = resp[4:4+data_length]
                    print(f"        數據部分: {data_section.hex().upper()}")
            else:
                print(f"     ❓ 未知格式響應")
    
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
    
    async def send_command_detailed(self, command, description, wait_time=2):
        """發送命令並詳細分析響應"""
        self.responses.clear()
        
        print(f"\n📤 {description}")
        print(f"   命令: {command.hex().upper()}")
        
        # 嘗試兩種寫入模式
        try:
            print("   寫入模式: response=False")
            await self.client.write_gatt_char(self.write_char, command, response=False)
            await asyncio.sleep(wait_time)
            
            if not self.responses:
                print("   無響應，嘗試 response=True")
                await self.client.write_gatt_char(self.write_char, command, response=True)
                await asyncio.sleep(wait_time)
            
        except Exception as e:
            print(f"   寫入錯誤: {e}")
        
        self.detailed_response_analysis(command, self.responses)
        return self.responses
    
    async def comprehensive_test(self):
        """全面協議測試"""
        if not await self.connect():
            return
            
        try:
            print("\n" + "="*70)
            print("🚀 修正版 Smart BMS 協議測試")
            print("="*70)
            
            # 1. 驗證校驗和算法
            self.verify_known_commands()
            
            # 2. 測試基本讀取命令
            print(f"\n📋 測試基本讀取命令:")
            
            for cmd_id, desc in [(0x03, "基本信息"), (0x04, "電芯電壓"), (0x05, "硬體信息")]:
                cmd = self.build_read_command_correct(cmd_id)
                await self.send_command_detailed(cmd, f"讀取{desc}")
                await asyncio.sleep(0.5)
            
            # 3. 嘗試 MOSFET 控制
            print(f"\n🔧 嘗試 MOSFET 控制:")
            
            # 預備命令
            preamble = self.build_write_command_correct(0x00, [0x56, 0x78])
            await self.send_command_detailed(preamble, "發送預備命令")
            
            # 開啟 MOSFET
            mosfet_on = self.build_write_command_correct(0xE1, [0x00, 0x00])
            await self.send_command_detailed(mosfet_on, "開啟 MOSFET")
            
            # 再次讀取狀態
            await asyncio.sleep(1)
            cmd = self.build_read_command_correct(0x03)
            await self.send_command_detailed(cmd, "確認最終狀態")
            
        except Exception as e:
            print(f"\n❌ 測試錯誤: {e}")
            
        finally:
            if self.client:
                await self.client.disconnect()
                print("\n👋 已斷開連接")

async def main():
    mac = "41:18:12:01:37:71"
    
    tester = CorrectSmartBMSProtocol(mac)
    await tester.comprehensive_test()

if __name__ == "__main__":
    print("🔬 修正版 Smart BMS 協議測試工具")
    print("使用正確的校驗和計算方法\n")
    asyncio.run(main())