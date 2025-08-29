#!/usr/bin/env python3
"""
簡單的藍牙 BLE 設備掃描工具
用於找到 DALY BMS 設備
"""

import asyncio
from bleak import BleakScanner

async def scan_for_devices():
    """掃描並列出所有藍牙設備"""
    print("🔍 開始掃描藍牙設備...")
    print("=" * 60)
    
    devices = await BleakScanner.discover(timeout=10.0)
    
    if not devices:
        print("❌ 沒有發現任何藍牙設備")
        return
    
    print(f"✅ 發現 {len(devices)} 個設備:")
    print()
    
    for i, device in enumerate(devices, 1):
        print(f"{i:2d}. MAC: {device.address}")
        print(f"    名稱: {device.name or '(未知)'}")
        try:
            print(f"    RSSI: {device.rssi} dBm")
        except:
            print(f"    RSSI: N/A")
        
        # 檢查是否可能是 DALY BMS
        is_possible_bms = False
        if device.name:
            name_lower = device.name.lower()
            if any(keyword in name_lower for keyword in ['daly', 'bms', 'battery']):
                is_possible_bms = True
        
        if device.address.startswith("41:18:12"):
            is_possible_bms = True
            
        if is_possible_bms:
            print("    🔋 *** 可能是 BMS 設備 ***")
        
        print()
    
    print("=" * 60)
    print("💡 提示:")
    print("- 查找名稱包含 'DALY', 'BMS', 'Battery' 的設備")
    print("- 或者 MAC 地址以 '41:18:12' 開頭的設備")
    print("- 記下正確的 MAC 地址用於後續連接")

if __name__ == "__main__":
    asyncio.run(scan_for_devices())