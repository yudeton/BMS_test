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
        """連接到 BMS (基於 POC 成功經驗)"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"嘗試連接 BMS {self.mac_address} ({attempt + 1}/{max_retries})")
                
                # 直接連接，不預掃描（POC 成功策略）
                self.client = BleakClient(self.mac_address)
                await self.client.connect(timeout=10.0)
                
                if not self.client.is_connected:
                    logger.warning("連接失敗")
                    if attempt < max_retries - 1:
                        logger.info("等待 2 秒後重試...")
                        await asyncio.sleep(2)
                        continue
                    return False
                
                logger.info("✅ BMS 連接成功！")
                
                # 啟用通知
                await self.client.start_notify(self.read_char, self.notification_handler)
                
                self.connected = True
                return True
                
            except Exception as e:
                logger.error(f"BMS 連接錯誤: {e}")
                if attempt < max_retries - 1:
                    logger.info("等待 2 秒後重試...")
                    await asyncio.sleep(2)
                    continue
                    
        self.connected = False
        logger.error("所有連接嘗試失敗")
        return False
    
    async def disconnect(self):
        """斷開 BMS 連接"""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
        self.connected = False
        logger.info("BMS 已斷開連接")
    
    async def send_command(self, command: bytes, timeout: float = 3.0, description: str = "") -> List[bytes]:
        """發送 BMS 命令並等待響應（增強版）"""
        self.responses.clear()
        
        try:
            if description:
                logger.debug(f"📤 {description}: {command.hex(' ').upper()}")
            else:
                logger.debug(f"📤 發送命令: {command.hex(' ').upper()}")
                
            await self.client.write_gatt_char(self.write_char, command, response=False)
            await asyncio.sleep(timeout)
            
            # 記錄響應
            for i, resp in enumerate(self.responses, 1):
                logger.debug(f"📥 響應 {i}: {resp.hex(' ').upper()}")
                
            return self.responses.copy()
            
        except Exception as e:
            logger.error(f"發送命令錯誤: {e}")
            return []
    
    def parse_modbus_response(self, command: bytes, response: bytes) -> Dict[str, Any]:
        """解析 Modbus 響應（增強版本）"""
        if len(response) < 5:
            return {"error": "響應太短"}
        
        # 檢查設備地址
        if response[0] != self.device_addr:
            return {"error": f"設備地址不匹配: 期望 0x{self.device_addr:02X}, 收到 0x{response[0]:02X}"}
        
        # 檢查功能碼
        if response[1] != 0x03:
            if response[1] & 0x80:  # 錯誤響應
                error_code = response[2] if len(response) > 2 else 0
                return {"error": f"Modbus 錯誤: 功能碼 0x{response[1]:02X}, 錯誤碼 0x{error_code:02X}"}
            else:
                return {"error": f"功能碼不匹配: 期望 0x03, 收到 0x{response[1]:02X}"}
        
        data_length = response[2]
        if len(response) < 3 + data_length + 2:
            return {"error": "數據長度不足"}
        
        data_bytes = response[3:3+data_length]
        
        # 驗證 CRC
        expected_crc = struct.unpack('<H', response[-2:])[0]  # 小端序
        calculated_crc = self.calculate_modbus_crc16(response[:-2])
        crc_valid = expected_crc == calculated_crc
        
        result = {
            "raw_data": data_bytes.hex().upper(),
            "data_length": data_length,
            "crc_valid": crc_valid
        }
        
        # 根據命令解析數據
        if len(command) >= 6:
            requested_addr = (command[2] << 8) | command[3]
            parsed_data = self.parse_register_data(requested_addr, data_bytes)
            result.update(parsed_data)
        
        return result
    
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
        """讀取完整 BMS 數據（基於 POC 成功策略）"""
        if not self.connected:
            logger.warning("BMS 未連接")
            return None
        
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "connection_status": "connected"
        }
        success = False
        
        try:
            # 使用 POC 成功的大範圍讀取策略
            logger.debug("使用大範圍讀取策略 (0x0000-0x003E)")
            cmd = self.build_modbus_command(0x0000, 0x003E)  # 讀取 62 個寄存器
            responses = await self.send_command(cmd, 4.0, "大範圍數據讀取")
            
            for response in responses:
                if response != cmd:  # 非回音響應
                    parsed = self.parse_modbus_response(cmd, response)
                    if "error" not in parsed and parsed.get("crc_valid", False):
                        logger.info("✅ 收到有效的大範圍響應！")
                        # 從大範圍數據中提取各種資訊
                        if self.extract_from_large_response(parsed, data):
                            success = True
                            break
            
            # 如果大範圍讀取失敗，使用個別讀取
            if not success:
                logger.debug("大範圍讀取失敗，嘗試個別寄存器讀取")
                success = await self.read_individual_registers(data)
            
            # 最終數據處理
            if success:
                # 計算功率
                if "total_voltage" in data and "current" in data:
                    data["power"] = data["total_voltage"] * data["current"]
                
                # 估算 SOC
                if "total_voltage" in data:
                    data["soc"] = self.estimate_soc(data["total_voltage"])
                
                self.read_count += 1
                self.last_read_time = time.time()
                data["status"] = "normal"
                logger.info(f"✅ BMS 數據讀取成功: {data.get('total_voltage', 'N/A')}V, {data.get('current', 'N/A')}A")
                return data
            
        except Exception as e:
            logger.error(f"讀取 BMS 數據錯誤: {e}")
            self.error_count += 1
            data["connection_status"] = "error"
            data["status"] = "error"
        
        return data if success else None
    
    def extract_from_large_response(self, parsed: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """從大範圍響應中提取數據"""
        try:
            raw_data = parsed.get("raw_data", "")
            if not raw_data or len(raw_data) < 160:  # 62*2*2 = 248 hex chars expected
                return False
            
            data_bytes = bytes.fromhex(raw_data)
            success = False
            
            # 提取總電壓 (地址 0x28 -> 位置 0x28*2 = 80)
            voltage_pos = 0x28 * 2
            if voltage_pos + 1 < len(data_bytes):
                raw_v = struct.unpack('>H', data_bytes[voltage_pos:voltage_pos+2])[0]
                if raw_v > 0:
                    data["total_voltage"] = raw_v * 0.1
                    success = True
                    logger.debug(f"提取總電壓: {data['total_voltage']}V")
            
            # 提取電流 (地址 0x29 -> 位置 0x29*2 = 82)
            current_pos = 0x29 * 2
            if current_pos + 1 < len(data_bytes):
                raw_i = struct.unpack('>H', data_bytes[current_pos:current_pos+2])[0]
                if raw_i >= 30000:
                    actual_current = (raw_i - 30000) * 0.1
                    data["current"] = actual_current
                    data["current_direction"] = "放電" if actual_current > 0 else "靜止"
                else:
                    actual_current = (30000 - raw_i) * 0.1
                    data["current"] = -actual_current
                    data["current_direction"] = "充電"
                success = True
                logger.debug(f"提取電流: {data['current']}A ({data['current_direction']})")
            
            # 提取電芯電壓 (地址 0x0000 開始)
            voltages = []
            for i in range(8):  # 8串電池
                pos = i * 2
                if pos + 1 < len(data_bytes):
                    raw_v = struct.unpack('>H', data_bytes[pos:pos+2])[0]
                    if raw_v > 0:
                        voltages.append(raw_v * 0.001)
            
            if voltages:
                data["cells"] = voltages
                logger.debug(f"提取電芯電壓: {len(voltages)} 串")
                success = True
            
            # 提取溫度 (地址 0x20 開始)
            temp_pos = 0x20 * 2
            temperatures = []
            for i in range(4):  # 4個溫度感測器
                pos = temp_pos + i * 2
                if pos + 1 < len(data_bytes):
                    raw_t = struct.unpack('>H', data_bytes[pos:pos+2])[0]
                    if raw_t > 0 and raw_t < 1000:
                        temp = (raw_t - 2731) * 0.1
                        temperatures.append(temp)
            
            if temperatures:
                data["temperatures"] = temperatures
                data["temperature"] = sum(temperatures) / len(temperatures)
                logger.debug(f"提取溫度: 平均 {data['temperature']:.1f}°C")
                success = True
            
            return success
            
        except Exception as e:
            logger.error(f"提取大範圍數據錯誤: {e}")
            return False
    
    async def read_individual_registers(self, data: Dict[str, Any]) -> bool:
        """個別寄存器讀取（備用策略）"""
        success = False
        
        # 讀取總電壓
        cmd = self.build_modbus_command(self.registers["total_voltage"], 1)
        responses = await self.send_command(cmd, 2.0, "讀取總電壓")
        
        for response in responses:
            if response != cmd:
                parsed = self.parse_modbus_response(cmd, response)
                if "total_voltage" in parsed:
                    data["total_voltage"] = parsed["total_voltage"]
                    success = True
                    break
        
        # 短暫延遲
        await asyncio.sleep(0.5)
        
        # 讀取電流
        cmd = self.build_modbus_command(self.registers["current"], 1)
        responses = await self.send_command(cmd, 2.0, "讀取電流")
        
        for response in responses:
            if response != cmd:
                parsed = self.parse_modbus_response(cmd, response)
                if "current" in parsed:
                    data["current"] = parsed["current"]
                    data["current_direction"] = parsed.get("current_direction")
                    success = True
                    break
        
        return success
    
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