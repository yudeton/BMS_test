import asyncio
import logging
import struct
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from bleak import BleakClient, BleakScanner

logger = logging.getLogger(__name__)

class BMSService:
    """BMS 通訊服務 - 整合現有的 D2 Modbus 協議"""
    
    def __init__(self, mac_address: str = "41:18:12:01:37:71"):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.connected = False
        self.responses = []
        
        # BLE 特徵值
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb"
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
        # D2 Modbus 設定
        self.device_addr = 0xD2
        self.registers = {
            "cell_voltage_base": 0x0000,  # 電芯電壓起始地址
            "temperature_base": 0x0020,   # 溫度起始地址
            "total_voltage": 0x0028,      # 總電壓
            "current": 0x0029,            # 電流
            "soc": 0x002C,               # SOC
            "mosfet_status": 0x002D,     # MOSFET 狀態
            "fault_bitmap": 0x003A,      # 故障狀態
        }
        
        # 統計信息
        self.read_count = 0
        self.error_count = 0
        self.last_read_time = None
    
    def calculate_modbus_crc16(self, data: bytes) -> int:
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
    
    def build_modbus_command(self, register_addr: int, num_registers: int = 1) -> bytes:
        """構建 Modbus 讀取命令"""
        packet = [
            self.device_addr,
            0x03,  # 讀取保持寄存器
            (register_addr >> 8) & 0xFF,
            register_addr & 0xFF,
            (num_registers >> 8) & 0xFF,
            num_registers & 0xFF
        ]
        
        crc = self.calculate_modbus_crc16(packet)
        packet.extend([crc & 0xFF, (crc >> 8) & 0xFF])
        return bytes(packet)
    
    def notification_handler(self, sender, data: bytes):
        """BLE 通知處理器"""
        if data:
            self.responses.append(data)
            logger.debug(f"收到 BMS 響應: {data.hex(' ').upper()}")
    
    async def connect(self) -> bool:
        """連接到 BMS"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"嘗試連接 BMS {self.mac_address} ({attempt + 1}/{max_retries})")
                
                self.client = BleakClient(self.mac_address)
                await self.client.connect(timeout=10.0)
                
                if not self.client.is_connected:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    return False
                
                # 啟用通知
                await self.client.start_notify(self.read_char, self.notification_handler)
                
                self.connected = True
                logger.info("BMS 連接成功")
                return True
                
            except Exception as e:
                logger.error(f"BMS 連接錯誤: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                    
        self.connected = False
        return False
    
    async def disconnect(self):
        """斷開 BMS 連接"""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
        self.connected = False
        logger.info("BMS 已斷開連接")
    
    async def send_command(self, command: bytes, timeout: float = 3.0) -> List[bytes]:
        """發送 BMS 命令並等待響應"""
        self.responses.clear()
        
        try:
            await self.client.write_gatt_char(self.write_char, command, response=False)
            await asyncio.sleep(timeout)
            return self.responses.copy()
            
        except Exception as e:
            logger.error(f"發送命令錯誤: {e}")
            return []
    
    def parse_modbus_response(self, command: bytes, response: bytes) -> Dict[str, Any]:
        """解析 Modbus 響應"""
        if len(response) < 5:
            return {"error": "響應太短"}
        
        if response[0] != self.device_addr or response[1] != 0x03:
            return {"error": "響應格式錯誤"}
        
        data_length = response[2]
        if len(response) < 3 + data_length + 2:
            return {"error": "數據長度不足"}
        
        data_bytes = response[3:3+data_length]
        
        # 根據命令解析數據
        if len(command) >= 6:
            requested_addr = (command[2] << 8) | command[3]
            return self.parse_register_data(requested_addr, data_bytes)
        
        return {"raw_data": data_bytes.hex()}
    
    def parse_register_data(self, register_addr: int, data: bytes) -> Dict[str, Any]:
        """解析特定寄存器的數據"""
        result = {}
        
        try:
            if register_addr == self.registers["total_voltage"] and len(data) >= 2:
                raw_voltage = struct.unpack('>H', data[:2])[0]
                result["total_voltage"] = raw_voltage * 0.1
                
            elif register_addr == self.registers["current"] and len(data) >= 2:
                raw_current = struct.unpack('>H', data[:2])[0]
                # 電流偏移編碼處理
                if raw_current >= 30000:
                    actual_current = (raw_current - 30000) * 0.1
                    result["current"] = actual_current
                    result["current_direction"] = "放電" if actual_current > 0 else "靜止"
                else:
                    actual_current = (30000 - raw_current) * 0.1
                    result["current"] = -actual_current
                    result["current_direction"] = "充電"
                    
            elif register_addr == self.registers["cell_voltage_base"]:
                # 電芯電壓
                voltages = []
                for i in range(0, min(len(data), 16), 2):
                    if i + 1 < len(data):
                        raw_v = struct.unpack('>H', data[i:i+2])[0]
                        if raw_v > 0:  # 有效電壓
                            voltages.append(raw_v * 0.001)
                result["cell_voltages"] = voltages
                
            elif register_addr == self.registers["temperature_base"]:
                # 溫度數據
                temperatures = []
                for i in range(0, min(len(data), 8), 2):
                    if i + 1 < len(data):
                        raw_t = struct.unpack('>H', data[i:i+2])[0]
                        if raw_t > 0 and raw_t < 1000:  # 合理溫度範圍
                            temp = (raw_t - 2731) * 0.1  # Kelvin 轉攝氏度
                            temperatures.append(temp)
                result["temperatures"] = temperatures
                
            elif register_addr == self.registers["soc"] and len(data) >= 2:
                raw_soc = struct.unpack('>H', data[:2])[0]
                result["soc"] = raw_soc * 0.1
                
        except Exception as e:
            logger.error(f"解析寄存器數據錯誤: {e}")
            result["parse_error"] = str(e)
        
        return result
    
    async def read_bms_data(self) -> Optional[Dict[str, Any]]:
        """讀取完整 BMS 數據"""
        if not self.connected:
            logger.warning("BMS 未連接")
            return None
        
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "connection_status": "connected"
        }
        success = False
        
        try:
            # 讀取總電壓
            cmd = self.build_modbus_command(self.registers["total_voltage"], 1)
            responses = await self.send_command(cmd, 2.0)
            
            for response in responses:
                if response != cmd:  # 非回音響應
                    parsed = self.parse_modbus_response(cmd, response)
                    if "total_voltage" in parsed:
                        data["total_voltage"] = parsed["total_voltage"]
                        success = True
                        break
            
            # 讀取電流
            cmd = self.build_modbus_command(self.registers["current"], 1)
            responses = await self.send_command(cmd, 2.0)
            
            for response in responses:
                if response != cmd:
                    parsed = self.parse_modbus_response(cmd, response)
                    if "current" in parsed:
                        data["current"] = parsed["current"]
                        data["current_direction"] = parsed.get("current_direction")
                        success = True
                        break
            
            # 計算功率
            if "total_voltage" in data and "current" in data:
                data["power"] = data["total_voltage"] * data["current"]
            
            # 讀取電芯電壓（8串）
            cmd = self.build_modbus_command(self.registers["cell_voltage_base"], 8)
            responses = await self.send_command(cmd, 2.0)
            
            for response in responses:
                if response != cmd:
                    parsed = self.parse_modbus_response(cmd, response)
                    if "cell_voltages" in parsed:
                        data["cells"] = parsed["cell_voltages"]
                        success = True
                        break
            
            # 讀取溫度（4個感測器）
            cmd = self.build_modbus_command(self.registers["temperature_base"], 4)
            responses = await self.send_command(cmd, 2.0)
            
            for response in responses:
                if response != cmd:
                    parsed = self.parse_modbus_response(cmd, response)
                    if "temperatures" in parsed:
                        data["temperatures"] = parsed["temperatures"]
                        # 計算平均溫度
                        if parsed["temperatures"]:
                            data["temperature"] = sum(parsed["temperatures"]) / len(parsed["temperatures"])
                        success = True
                        break
            
            # 估算 SOC（基於電壓）
            if "total_voltage" in data:
                data["soc"] = self.estimate_soc(data["total_voltage"])
            
            if success:
                self.read_count += 1
                self.last_read_time = time.time()
                data["status"] = "normal"
                logger.debug(f"BMS 數據讀取成功: {data.get('total_voltage')}V, {data.get('current')}A")
                return data
            
        except Exception as e:
            logger.error(f"讀取 BMS 數據錯誤: {e}")
            self.error_count += 1
            data["connection_status"] = "error"
            data["status"] = "error"
        
        return data if success else None
    
    def estimate_soc(self, voltage: float) -> float:
        """基於電壓估算 SOC（8S LiFePO4）"""
        # 8S LiFePO4 電壓範圍：24.0V (0%) - 29.6V (100%)
        min_voltage = 24.0
        max_voltage = 29.6
        
        if voltage <= min_voltage:
            return 0.0
        elif voltage >= max_voltage:
            return 100.0
        else:
            soc = ((voltage - min_voltage) / (max_voltage - min_voltage)) * 100
            return round(soc, 1)
    
    async def wake_bms(self):
        """喚醒 BMS"""
        if self.connected:
            try:
                # 發送喚醒命令
                cmd = self.build_modbus_command(self.registers["total_voltage"], 1)
                await self.send_command(cmd, 1.0)
                logger.info("BMS 喚醒命令已發送")
            except Exception as e:
                logger.error(f"喚醒 BMS 錯誤: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        return {
            "connected": self.connected,
            "mac_address": self.mac_address,
            "read_count": self.read_count,
            "error_count": self.error_count,
            "last_read_time": self.last_read_time,
            "success_rate": (self.read_count / (self.read_count + self.error_count)) * 100 if (self.read_count + self.error_count) > 0 else 0
        }