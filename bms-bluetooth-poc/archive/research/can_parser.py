#!/usr/bin/env python3
"""
CAN 協議解析器
根據你的 BMS CAN 通訊協議解析數據
"""

from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
from config import (
    CAN_ID_BMS_TO_CHARGER,
    CAN_ID_CHARGER_BROADCAST,
    VOLTAGE_SCALE,
    CURRENT_SCALE,
    SOC_SCALE,
    STATUS_FLAGS
)

class MessageType(Enum):
    """報文類型"""
    BMS_CONTROL = 1  # 報文1: BMS → 充電機
    CHARGER_STATUS = 2  # 報文2: 充電機 → 廣播
    UNKNOWN = 0

@dataclass
class BMSData:
    """BMS 數據結構 (報文1)"""
    can_id: int
    max_charge_voltage: float  # 最高允許充電端電壓 (V)
    max_charge_current: float  # 最高允許充電電流 (A)
    soc: float                 # 當前 SOC (%)
    control: int                # 控制狀態 (0=充電開啟, 1=充電關閉)
    status: int                 # 異常狀態 (0=正常, 1=異常)
    raw_data: bytes

@dataclass
class ChargerData:
    """充電機數據結構 (報文2)"""
    can_id: int
    output_voltage: float  # 輸出電壓 (V)
    output_current: float  # 輸出電流 (A)
    soc: float            # 當前 SOC (%)
    status_flags: int     # 狀態標誌位
    raw_data: bytes

class CANParser:
    """CAN 協議解析器"""
    
    def __init__(self):
        self.last_bms_data: Optional[BMSData] = None
        self.last_charger_data: Optional[ChargerData] = None
    
    def parse_can_frame(self, data: bytes) -> Tuple[Optional[int], Optional[bytes]]:
        """
        解析 CAN 幀
        返回: (CAN_ID, 數據部分)
        """
        if len(data) < 12:  # CAN 幀至少需要 12 bytes (4 bytes ID + 8 bytes 數據)
            return None, None
        
        # 解析 29 位 CAN ID (假設前 4 bytes 是 CAN ID)
        can_id = int.from_bytes(data[:4], byteorder='big') & 0x1FFFFFFF
        
        # 獲取數據部分 (8 bytes)
        can_data = data[4:12]
        
        return can_id, can_data
    
    def identify_message_type(self, can_id: int) -> MessageType:
        """識別報文類型"""
        if can_id == CAN_ID_BMS_TO_CHARGER:
            return MessageType.BMS_CONTROL
        elif can_id == CAN_ID_CHARGER_BROADCAST:
            return MessageType.CHARGER_STATUS
        else:
            return MessageType.UNKNOWN
    
    def parse_bms_control_message(self, data: bytes) -> Optional[BMSData]:
        """
        解析報文1: BMS 控制信息
        數據格式:
        - Byte 1-2: 最高允許充電端電壓 (0.1V/bit)
        - Byte 3-4: 最高允許充電電流 (0.1A/bit)
        - Byte 5-6: 當前 SOC (0.1%/bit)
        - Byte 7: 控制 (0=充電開啟, 1=充電關閉)
        - Byte 8: 異常說明 (0=正常, 1=異常)
        """
        if len(data) < 8:
            return None
        
        try:
            # 解析電壓 (高字節在前)
            voltage_raw = (data[0] << 8) | data[1]
            voltage = voltage_raw * VOLTAGE_SCALE
            
            # 解析電流
            current_raw = (data[2] << 8) | data[3]
            current = current_raw * CURRENT_SCALE
            
            # 解析 SOC
            soc_raw = (data[4] << 8) | data[5]
            soc = soc_raw * SOC_SCALE
            
            # 解析控制和狀態
            control = data[6]
            status = data[7]
            
            bms_data = BMSData(
                can_id=CAN_ID_BMS_TO_CHARGER,
                max_charge_voltage=voltage,
                max_charge_current=current,
                soc=soc,
                control=control,
                status=status,
                raw_data=data
            )
            
            self.last_bms_data = bms_data
            return bms_data
            
        except Exception as e:
            print(f"解析 BMS 控制報文失敗: {e}")
            return None
    
    def parse_charger_status_message(self, data: bytes) -> Optional[ChargerData]:
        """
        解析報文2: 充電機狀態
        數據格式:
        - Byte 1-2: 輸出電壓 (0.1V/bit)
        - Byte 3-4: 輸出電流 (0.1A/bit)
        - Byte 5-6: 當前 SOC (0.1%/bit)
        - Byte 7: 狀態標誌
        - Byte 8: 保留
        """
        if len(data) < 8:
            return None
        
        try:
            # 解析電壓
            voltage_raw = (data[0] << 8) | data[1]
            voltage = voltage_raw * VOLTAGE_SCALE
            
            # 解析電流
            current_raw = (data[2] << 8) | data[3]
            current = current_raw * CURRENT_SCALE
            
            # 解析 SOC
            soc_raw = (data[4] << 8) | data[5]
            soc = soc_raw * SOC_SCALE
            
            # 解析狀態標誌
            status_flags = data[6]
            
            charger_data = ChargerData(
                can_id=CAN_ID_CHARGER_BROADCAST,
                output_voltage=voltage,
                output_current=current,
                soc=soc,
                status_flags=status_flags,
                raw_data=data
            )
            
            self.last_charger_data = charger_data
            return charger_data
            
        except Exception as e:
            print(f"解析充電機狀態報文失敗: {e}")
            return None
    
    def parse_status_flags(self, flags: int) -> Dict[str, bool]:
        """解析狀態標誌位"""
        parsed_flags = {}
        
        for bit, description in STATUS_FLAGS.items():
            parsed_flags[description] = bool(flags & (1 << bit))
        
        return parsed_flags
    
    def parse(self, raw_data: bytes) -> Dict:
        """
        解析原始數據
        返回解析後的字典格式
        """
        result = {
            "raw_hex": raw_data.hex(),
            "length": len(raw_data),
            "parsed": False,
            "message_type": None,
            "data": None
        }
        
        # 解析 CAN 幀
        can_id, can_data = self.parse_can_frame(raw_data)
        
        if can_id is None or can_data is None:
            result["error"] = "無效的 CAN 幀格式"
            return result
        
        result["can_id"] = f"0x{can_id:08X}"
        
        # 識別報文類型
        msg_type = self.identify_message_type(can_id)
        result["message_type"] = msg_type.name
        
        # 根據類型解析數據
        if msg_type == MessageType.BMS_CONTROL:
            bms_data = self.parse_bms_control_message(can_data)
            if bms_data:
                result["parsed"] = True
                result["data"] = {
                    "type": "BMS 控制信息",
                    "max_voltage": f"{bms_data.max_charge_voltage:.1f} V",
                    "max_current": f"{bms_data.max_charge_current:.1f} A",
                    "soc": f"{bms_data.soc:.1f} %",
                    "charging": "開啟" if bms_data.control == 0 else "關閉",
                    "status": "正常" if bms_data.status == 0 else "異常",
                    "power": f"{bms_data.max_charge_voltage * bms_data.max_charge_current:.1f} W"
                }
                
        elif msg_type == MessageType.CHARGER_STATUS:
            charger_data = self.parse_charger_status_message(can_data)
            if charger_data:
                result["parsed"] = True
                flags = self.parse_status_flags(charger_data.status_flags)
                result["data"] = {
                    "type": "充電機狀態",
                    "output_voltage": f"{charger_data.output_voltage:.1f} V",
                    "output_current": f"{charger_data.output_current:.1f} A",
                    "soc": f"{charger_data.soc:.1f} %",
                    "power": f"{charger_data.output_voltage * charger_data.output_current:.1f} W",
                    "status_flags": flags
                }
        
        return result
    
    def format_display(self, parsed_data: Dict) -> str:
        """格式化顯示解析結果"""
        lines = []
        lines.append("=" * 50)
        lines.append(f"原始數據: {parsed_data['raw_hex']}")
        lines.append(f"數據長度: {parsed_data['length']} bytes")
        
        if parsed_data.get("can_id"):
            lines.append(f"CAN ID: {parsed_data['can_id']}")
            lines.append(f"報文類型: {parsed_data.get('message_type', '未知')}")
        
        if parsed_data["parsed"] and parsed_data.get("data"):
            data = parsed_data["data"]
            lines.append("-" * 50)
            lines.append(f"類型: {data.get('type', '')}")
            
            for key, value in data.items():
                if key not in ["type", "status_flags"]:
                    lines.append(f"  {key}: {value}")
            
            # 顯示狀態標誌
            if "status_flags" in data:
                lines.append("  狀態標誌:")
                for flag, active in data["status_flags"].items():
                    if active:
                        lines.append(f"    ⚠️  {flag}")
        
        elif parsed_data.get("error"):
            lines.append(f"錯誤: {parsed_data['error']}")
        
        lines.append("=" * 50)
        return "\n".join(lines)

# 測試用函數
def test_parser():
    """測試解析器"""
    parser = CANParser()
    
    # 模擬報文1數據 (BMS 控制)
    # CAN ID: 0x1806E5F4, 電壓: 320.1V, 電流: 58.2A, SOC: 58.2%, 充電開啟, 正常
    test_data1 = bytes.fromhex("1806E5F4 0C81 0246 0246 00 00".replace(" ", ""))
    
    # 模擬報文2數據 (充電機狀態)
    test_data2 = bytes.fromhex("18FF50E5 0C81 0246 0246 00 00".replace(" ", ""))
    
    print("測試報文1 (BMS 控制):")
    result1 = parser.parse(test_data1)
    print(parser.format_display(result1))
    
    print("\n測試報文2 (充電機狀態):")
    result2 = parser.parse(test_data2)
    print(parser.format_display(result2))

if __name__ == "__main__":
    test_parser()