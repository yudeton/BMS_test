#!/usr/bin/env python3
"""
簡單協議測試
"""

import asyncio
import sys
from bleak import BleakClient

async def test_discovered_command():
    mac = "41:18:12:01:37:71"
    
    # 發現的最佳命令
    cmd_hex = "A58093080000000000000000C0"
    command = bytes.fromhex(cmd_hex)
    
    responses = []
    
    def notification_handler(sender, data):
        if data:
            responses.append(data.hex().upper())
            print(f"收到響應: {data.hex().upper()}")
    
    try:
        print(f"連接到 {mac}...")
        
        # 先找設備
        from bleak import BleakScanner
        device = await BleakScanner.find_device_by_address(mac, timeout=5.0)
        if not device:
            print("找不到設備")
            return
            
        client = BleakClient(mac)
        await client.connect()
        
        if not client.is_connected:
            print("連接失敗")
            return
            
        print("✅ 連接成功!")
        
        # 使用 fff1 和 fff2 特徵
        write_char = "0000fff2-0000-1000-8000-00805f9b34fb"
        read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
        print(f"測試命令: {cmd_hex}")
        
        # 啟用通知
        await client.start_notify(read_char, notification_handler)
        
        # 發送命令
        await client.write_gatt_char(write_char, command, response=False)
        print("命令已發送，等待響應...")
        
        # 等待響應
        await asyncio.sleep(3)
        
        # 停止通知
        await client.stop_notify(read_char)
        
        print(f"\n結果:")
        if responses:
            for i, resp in enumerate(responses, 1):
                print(f"  響應 {i}: {resp}")
                
                # 快速分析
                if len(resp) == 26:  # 13 bytes * 2 hex chars
                    data = bytes.fromhex(resp)
                    if data[0] == 0xA5 and len(data) == 13:
                        print(f"    A5協議響應！")
                        
                        # 檢查MOSFET狀態解析
                        if data[2] == 0x93:  # MOSFET命令
                            payload = data[4:12]
                            charge_mos = "開啟" if payload[0] == 1 else "關閉" 
                            discharge_mos = "開啟" if payload[1] == 1 else "關閉"
                            
                            print(f"    充電MOSFET: {charge_mos}")
                            print(f"    放電MOSFET: {discharge_mos}")
                            
                            # 嘗試提取電壓
                            for j in range(len(payload) - 1):
                                voltage = int.from_bytes(payload[j:j+2], 'big') / 10.0
                                if 10.0 <= voltage <= 60.0:  
                                    print(f"    可能電壓: {voltage:.1f}V")
        else:
            print("  無響應")
            
        await client.disconnect()
        
    except Exception as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    asyncio.run(test_discovered_command())