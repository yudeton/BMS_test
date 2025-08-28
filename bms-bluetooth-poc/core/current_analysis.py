#!/usr/bin/env python3
"""
電流數據分析工具
分析原始數據 0x7530 的各種可能解析方式
"""

import struct

def analyze_current_data():
    """分析電流數據的各種解析可能性"""
    raw_hex = "7530"
    raw_bytes = bytes.fromhex(raw_hex)
    
    print("🔬 電流數據分析")
    print(f"原始數據: 0x{raw_hex}")
    print("=" * 50)
    
    # 1. 無符號 16位元 大端序
    val_u16_be = struct.unpack('>H', raw_bytes)[0]
    print(f"無符號16位 (大端): {val_u16_be}")
    print(f"  * 0.1   = {val_u16_be * 0.1:.1f}A")
    print(f"  * 0.01  = {val_u16_be * 0.01:.2f}A")
    print(f"  * 0.001 = {val_u16_be * 0.001:.3f}A")
    print()
    
    # 2. 有符號 16位元 大端序
    val_s16_be = struct.unpack('>h', raw_bytes)[0]
    print(f"有符號16位 (大端): {val_s16_be}")
    print(f"  * 0.1   = {val_s16_be * 0.1:.1f}A")
    print(f"  * 0.01  = {val_s16_be * 0.01:.2f}A")
    print(f"  * 0.001 = {val_s16_be * 0.001:.3f}A")
    print()
    
    # 3. 無符號 16位元 小端序
    val_u16_le = struct.unpack('<H', raw_bytes)[0]
    print(f"無符號16位 (小端): {val_u16_le}")
    print(f"  * 0.1   = {val_u16_le * 0.1:.1f}A")
    print(f"  * 0.01  = {val_u16_le * 0.01:.2f}A")
    print(f"  * 0.001 = {val_u16_le * 0.001:.3f}A")
    print()
    
    # 4. 特殊編碼分析
    print("🔍 特殊編碼分析:")
    
    # BCD 編碼？
    bcd_1 = (raw_bytes[0] >> 4) * 1000 + (raw_bytes[0] & 0xF) * 100
    bcd_2 = (raw_bytes[1] >> 4) * 10 + (raw_bytes[1] & 0xF)
    bcd_value = bcd_1 + bcd_2
    print(f"BCD編碼: {bcd_value}")
    print(f"  * 0.1   = {bcd_value * 0.1:.1f}A")
    print(f"  * 0.01  = {bcd_value * 0.01:.2f}A")
    print()
    
    # 5. 偏移量編碼 (常用於電流，因為需要表示負值)
    print("🔋 偏移量編碼分析 (電流可能有偏移):")
    offsets = [32768, 30000, 40000]  # 常見偏移值
    for offset in offsets:
        offset_val = val_u16_be - offset
        print(f"偏移 {offset}: {offset_val}")
        print(f"  * 0.1   = {offset_val * 0.1:.1f}A")
        print(f"  * 0.01  = {offset_val * 0.01:.2f}A")
        print()
    
    # 6. 合理電流範圍分析
    print("⚡ 合理電流範圍分析:")
    print("對於家用電池系統，合理電流通常在:")
    print("- 充電: 0-50A")
    print("- 放電: 0-100A") 
    print("- 靜態: 接近0A")
    print()
    
    reasonable_candidates = []
    
    # 檢查各種解析是否合理
    candidates = [
        ("無符號*0.1", val_u16_be * 0.1),
        ("無符號*0.01", val_u16_be * 0.01),
        ("無符號*0.001", val_u16_be * 0.001),
        ("有符號*0.1", val_s16_be * 0.1),
        ("有符號*0.01", val_s16_be * 0.01),
        ("小端*0.1", val_u16_le * 0.1),
        ("小端*0.01", val_u16_le * 0.01),
        ("偏移32768*0.1", (val_u16_be - 32768) * 0.1),
        ("偏移30000*0.1", (val_u16_be - 30000) * 0.1),
    ]
    
    for name, value in candidates:
        if -200 <= value <= 200:  # 合理電流範圍
            reasonable_candidates.append((name, value))
    
    print("✅ 可能的合理解析:")
    for name, value in reasonable_candidates:
        print(f"  {name}: {value:.2f}A")

if __name__ == "__main__":
    analyze_current_data()