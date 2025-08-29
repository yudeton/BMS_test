#!/usr/bin/env python3
"""
BMS 喚醒測試工具
嘗試各種方法喚醒可能休眠的 BMS
"""

import asyncio
import time
from bleak import BleakClient, BleakScanner

class BMSWakeTester:
    def __init__(self):
        self.mac = "41:18:12:01:37:71"
        self.found_device = False
        
    async def quick_scan_attempt(self, timeout=3):
        """快速掃描嘗試"""
        try:
            print(f"🔍 快速掃描 ({timeout}秒)...")
            device = await BleakScanner.find_device_by_address(self.mac, timeout=timeout)
            if device:
                print(f"✅ 找到設備: {device.name} (RSSI: {getattr(device, 'rssi', 'N/A')})")
                self.found_device = True
                return device
            else:
                print("❌ 未找到設備")
                return None
        except Exception as e:
            print(f"❌ 掃描錯誤: {e}")
            return None
    
    async def connection_attempt(self, device):
        """連接嘗試"""
        if not device:
            return False
            
        try:
            print(f"🔌 嘗試連接...")
            client = BleakClient(device)
            await client.connect(timeout=5)
            
            if client.is_connected:
                print("✅ 連接成功!")
                await client.disconnect()
                return True
            else:
                print("❌ 連接失敗")
                return False
                
        except Exception as e:
            print(f"❌ 連接錯誤: {e}")
            return False
    
    async def wake_up_sequence(self):
        """喚醒序列"""
        print("🌅 BMS 喚醒測試序列")
        print("=" * 50)
        
        # 策略 1: 多次快速掃描
        print("\n📡 策略 1: 多次快速掃描")
        for attempt in range(5):
            print(f"\n嘗試 {attempt + 1}/5:")
            device = await self.quick_scan_attempt(3)
            
            if device:
                # 如果找到設備，嘗試連接
                if await self.connection_attempt(device):
                    print("🎉 BMS 已喚醒並可連接!")
                    return True
                else:
                    print("⚠️ 設備可見但無法連接，可能仍在喚醒中...")
            
            # 等待一下再試
            print("⏳ 等待 2 秒...")
            await asyncio.sleep(2)
        
        # 策略 2: 延長掃描時間
        print("\n📡 策略 2: 延長掃描時間 (10秒)")
        device = await self.quick_scan_attempt(10)
        if device:
            if await self.connection_attempt(device):
                print("🎉 BMS 已喚醒並可連接!")
                return True
        
        # 策略 3: 持續監控模式
        print("\n📡 策略 3: 持續監控模式")
        print("持續掃描 30 秒，等待 BMS 出現...")
        
        start_time = time.time()
        while time.time() - start_time < 30:
            device = await self.quick_scan_attempt(2)
            if device:
                if await self.connection_attempt(device):
                    print("🎉 BMS 已喚醒並可連接!")
                    return True
            
            # 短暫休息
            await asyncio.sleep(1)
        
        print("❌ 所有喚醒策略都失敗了")
        return False

async def main():
    tester = BMSWakeTester()
    success = await tester.wake_up_sequence()
    
    if success:
        print("\n✅ BMS 喚醒成功！現在可以運行 D2 協議測試")
        print("執行: python3 quick_d2_test.py")
    else:
        print("\n❌ BMS 可能處於深度休眠狀態")
        print("\n🔧 建議排除方法:")
        print("1. 檢查 BMS 是否有實體喚醒按鈕")
        print("2. 短暫連接充電器觸發喚醒")
        print("3. 檢查電池是否有足夠電量")
        print("4. 嘗試使用 Smart BMS app 連接一次後立即斷開")

if __name__ == "__main__":
    print("🌅 BMS 喚醒測試工具")
    asyncio.run(main())