#!/usr/bin/env python3
"""
BMS MQTT 數據橋接程式
整合 DALY BMS D2 Modbus 協議與 Web 監控系統

功能:
- 持續讀取 BMS 數據 (30秒間隔)
- 自動 BMS 喚醒與重連
- 數據格式轉換
- MQTT 發送到 Web 監控系統
"""

import asyncio
import json
import logging
import struct
import time
from datetime import datetime
from typing import Dict, Any, Optional

import paho.mqtt.client as mqtt
from bleak import BleakClient, BleakScanner

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bms_mqtt_bridge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BMSMQTTBridge:
    def __init__(self, bms_mac: str = "41:18:12:01:37:71"):
        self.bms_mac = bms_mac
        self.client = None
        self.mqtt_client = mqtt.Client()
        self.running = False
        
        # BLE 特徵值
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb"
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
        # D2 Modbus 設定
        self.device_addr = 0xD2
        self.registers = {
            "cell_voltage_base": 0x0000,
            "temperature_base": 0x0020,
            "total_voltage": 0x0028,
            "current": 0x0029,
            "soc": 0x002C,
            "mosfet_status": 0x002D,
            "fault_bitmap": 0x003A,
        }
        
        # 數據儲存
        self.latest_data = {}
        self.responses = []
        
        # MQTT 設定
        self.mqtt_broker = "localhost"
        self.mqtt_port = 1883
        self.mqtt_topics = {
            "realtime": "battery/realtime",
            "alerts": "battery/alerts",
            "status": "battery/status"
        }
        
        # 系統狀態
        self.last_read_time = None
        self.read_count = 0
        self.error_count = 0
        
    def setup_mqtt(self):
        """設定 MQTT 連接"""
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info(f"MQTT 連接成功: {self.mqtt_broker}:{self.mqtt_port}")
            else:
                logger.error(f"MQTT 連接失敗，錯誤碼: {rc}")
                
        def on_disconnect(client, userdata, rc):
            logger.warning(f"MQTT 連接斷開，錯誤碼: {rc}")
            
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_disconnect = on_disconnect
        
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            logger.error(f"MQTT 連接設定失敗: {e}")
            return False
            
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
        """構建 Modbus 讀取命令"""
        packet = [
            self.device_addr,
            0x03,
            (register_addr >> 8) & 0xFF,
            register_addr & 0xFF,
            (num_registers >> 8) & 0xFF,
            num_registers & 0xFF
        ]
        
        crc = self.calculate_modbus_crc16(packet)
        packet.extend([crc & 0xFF, (crc >> 8) & 0xFF])
        return bytes(packet)
        
    def notification_handler(self, sender, data):
        """處理 BLE 通知數據"""
        if data:
            self.responses.append(data)
            logger.debug(f"收到響應: {data.hex(' ').upper()} ({len(data)} bytes)")
            
    async def bms_wake_attempt(self, max_attempts=5):
        """BMS 喚醒嘗試"""
        for attempt in range(max_attempts):
            try:
                logger.info(f"BMS 喚醒嘗試 {attempt + 1}/{max_attempts}")
                
                device = await BleakScanner.find_device_by_address(self.bms_mac, timeout=3.0)
                if not device:
                    logger.warning(f"未找到設備，嘗試 {attempt + 1}")
                    await asyncio.sleep(2)
                    continue
                    
                # 嘗試連接
                test_client = BleakClient(device)
                await test_client.connect(timeout=5)
                
                if test_client.is_connected:
                    logger.info("BMS 喚醒成功!")
                    await test_client.disconnect()
                    return True
                    
            except Exception as e:
                logger.warning(f"喚醒嘗試 {attempt + 1} 失敗: {e}")
                await asyncio.sleep(2)
                
        logger.error("BMS 喚醒失敗")
        return False
        
    async def connect_bms(self):
        """連接到 BMS"""
        try:
            logger.info(f"連接到 BMS: {self.bms_mac}")
            self.client = BleakClient(self.bms_mac)
            await self.client.connect(timeout=10.0)
            
            if not self.client.is_connected:
                return False
                
            # 啟用通知
            await self.client.start_notify(self.read_char, self.notification_handler)
            logger.info("BMS 連接成功，通知已啟用")
            return True
            
        except Exception as e:
            logger.error(f"BMS 連接失敗: {e}")
            return False
            
    async def send_modbus_command(self, command, description, wait_time=3):
        """發送 Modbus 命令並等待響應"""
        self.responses.clear()
        
        logger.debug(f"發送命令: {description}")
        
        try:
            await self.client.write_gatt_char(self.write_char, command, response=False)
            await asyncio.sleep(wait_time)
            
            if self.responses:
                return self.responses[0]  # 返回第一個響應
            else:
                logger.warning(f"命令無響應: {description}")
                return None
                
        except Exception as e:
            logger.error(f"命令發送失敗: {e}")
            return None
            
    def parse_voltage_data(self, data, scale=0.1):
        """解析電壓數據"""
        if len(data) >= 2:
            raw_value = struct.unpack('>H', data[:2])[0]
            return raw_value * scale
        return None
        
    def parse_current_data(self, data):
        """解析電流數據 (使用偏移編碼)"""
        if len(data) >= 2:
            raw_current = struct.unpack('>H', data[:2])[0]
            # 使用30000作為零點偏移
            if raw_current >= 30000:
                actual_current = (raw_current - 30000) * 0.1
                direction = "放電" if actual_current > 0.1 else "靜止"
            else:
                actual_current = (30000 - raw_current) * 0.1
                actual_current = -actual_current  # 充電為負值
                direction = "充電"
                
            return {
                "current": actual_current,
                "direction": direction,
                "raw": raw_current
            }
        return None
        
    def parse_cell_voltages(self, data):
        """解析電芯電壓數據"""
        voltages = []
        for i in range(0, min(len(data), 16), 2):
            if i + 1 < len(data):
                raw_v = struct.unpack('>H', data[i:i+2])[0]
                voltages.append(raw_v * 0.001)  # 0.001V 解析度
        return voltages
        
    def parse_temperatures(self, data):
        """解析溫度數據"""
        temperatures = []
        for i in range(0, min(len(data), 8), 2):
            if i + 1 < len(data):
                raw_temp = struct.unpack('>H', data[i:i+2])[0]
                # DALY BMS 溫度格式：需要減去偏移值並轉換
                # 通常使用 0.1 度解析度，並有偏移值
                if raw_temp == 0 or raw_temp > 1000:  # 無效數據過濾
                    continue
                actual_temp = (raw_temp - 2731) / 10.0  # 開爾文轉攝氏度的常見格式
                if -40 <= actual_temp <= 80:  # 合理溫度範圍
                    temperatures.append(actual_temp)
        return temperatures
        
    def calculate_soc(self, total_voltage, cell_voltages):
        """基於電壓估算 SOC"""
        if not total_voltage:
            return None
            
        # 8S LiFePO4 電池 SOC 估算
        # 滿電: 29.6V (3.7V × 8), 空電: 24.0V (3.0V × 8)
        voltage_range = 29.6 - 24.0
        current_range = total_voltage - 24.0
        
        if current_range <= 0:
            return 0
        elif current_range >= voltage_range:
            return 100
        else:
            soc = (current_range / voltage_range) * 100
            return round(soc, 1)
            
    async def read_bms_data(self):
        """讀取完整 BMS 數據"""
        data = {}
        
        try:
            # 讀取總電壓
            cmd = self.build_modbus_read_command(self.registers["total_voltage"], 1)
            response = await self.send_modbus_command(cmd, "讀取總電壓")
            if response and len(response) > 4:
                voltage = self.parse_voltage_data(response[3:-2])  # 跳過頭部和CRC
                data["total_voltage"] = voltage
                
            # 讀取電流
            cmd = self.build_modbus_read_command(self.registers["current"], 1)
            response = await self.send_modbus_command(cmd, "讀取電流")
            if response and len(response) > 4:
                current_info = self.parse_current_data(response[3:-2])
                if current_info:
                    data.update(current_info)
                    
            # 讀取電芯電壓 (8串)
            cmd = self.build_modbus_read_command(self.registers["cell_voltage_base"], 8)
            response = await self.send_modbus_command(cmd, "讀取電芯電壓")
            if response and len(response) > 4:
                cell_voltages = self.parse_cell_voltages(response[3:-2])
                data["cell_voltages"] = cell_voltages
                
            # 讀取溫度
            cmd = self.build_modbus_read_command(self.registers["temperature_base"], 4)
            response = await self.send_modbus_command(cmd, "讀取溫度")
            if response and len(response) > 4:
                temperatures = self.parse_temperatures(response[3:-2])
                data["temperatures"] = temperatures
                
            # 計算衍生數據
            if "total_voltage" in data and "current" in data:
                data["power"] = data["total_voltage"] * abs(data["current"])
                
            if "total_voltage" in data:
                data["soc"] = self.calculate_soc(
                    data["total_voltage"], 
                    data.get("cell_voltages", [])
                )
                
            if "temperatures" in data:
                data["avg_temperature"] = sum(data["temperatures"]) / len(data["temperatures"])
                
            # 系統狀態
            data["status"] = "normal"  # 基礎狀態，後續可增加邏輯
            data["timestamp"] = datetime.now().isoformat()
            data["read_count"] = self.read_count
            
            self.latest_data = data
            self.last_read_time = time.time()
            self.read_count += 1
            
            logger.info(f"BMS 數據讀取成功: {data.get('total_voltage', 'N/A')}V, "
                       f"{data.get('current', 'N/A')}A, {len(data.get('cell_voltages', []))}串")
            
            return data
            
        except Exception as e:
            logger.error(f"BMS 數據讀取失敗: {e}")
            self.error_count += 1
            return None
            
    def format_mqtt_data(self, bms_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化數據為 MQTT 發送格式"""
        if not bms_data:
            return None
            
        mqtt_data = {
            "timestamp": bms_data.get("timestamp"),
            "voltage": bms_data.get("total_voltage"),
            "current": bms_data.get("current", 0.0),
            "power": bms_data.get("power", 0.0),
            "soc": bms_data.get("soc"),
            "temperature": bms_data.get("avg_temperature"),
            "status": bms_data.get("status", "unknown"),
            "cells": bms_data.get("cell_voltages", []),
            "temperatures": bms_data.get("temperatures", []),
            "metadata": {
                "bms_model": "DALY_D2_MODBUS",
                "firmware": "K00T",
                "cell_count": len(bms_data.get("cell_voltages", [])),
                "read_count": bms_data.get("read_count", 0),
                "current_direction": bms_data.get("direction", "unknown")
            }
        }
        
        return mqtt_data
        
    async def publish_mqtt_data(self, data: Dict[str, Any]):
        """發布數據到 MQTT"""
        try:
            mqtt_data = self.format_mqtt_data(data)
            if not mqtt_data:
                return
                
            # 發布即時數據
            payload = json.dumps(mqtt_data, ensure_ascii=False, indent=2)
            result = self.mqtt_client.publish(self.mqtt_topics["realtime"], payload)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug("MQTT 數據發送成功")
            else:
                logger.warning(f"MQTT 數據發送失敗，錯誤碼: {result.rc}")
                
            # 檢查並發送警報
            await self.check_and_send_alerts(mqtt_data)
            
        except Exception as e:
            logger.error(f"MQTT 數據發布失敗: {e}")
            
    async def check_and_send_alerts(self, data: Dict[str, Any]):
        """檢查並發送警報"""
        alerts = []
        
        # 電壓警報檢查
        voltage = data.get("voltage")
        if voltage:
            if voltage < 24.0:
                alerts.append({
                    "type": "critical_low_voltage",
                    "severity": "critical",
                    "message": f"電池總電壓極低: {voltage:.1f}V",
                    "value": voltage,
                    "threshold": 24.0
                })
            elif voltage < 25.6:
                alerts.append({
                    "type": "low_voltage",
                    "severity": "warning", 
                    "message": f"電池總電壓偏低: {voltage:.1f}V",
                    "value": voltage,
                    "threshold": 25.6
                })
            elif voltage > 30.4:
                alerts.append({
                    "type": "high_voltage",
                    "severity": "critical",
                    "message": f"電池總電壓過高: {voltage:.1f}V", 
                    "value": voltage,
                    "threshold": 30.4
                })
                
        # 電芯電壓警報檢查
        cells = data.get("cells", [])
        for i, cell_v in enumerate(cells):
            if cell_v < 3.0:
                alerts.append({
                    "type": "critical_cell_voltage",
                    "severity": "critical",
                    "message": f"電芯 {i+1} 電壓極低: {cell_v:.3f}V",
                    "value": cell_v,
                    "cell": i+1,
                    "threshold": 3.0
                })
            elif cell_v > 3.8:
                alerts.append({
                    "type": "high_cell_voltage", 
                    "severity": "warning",
                    "message": f"電芯 {i+1} 電壓偏高: {cell_v:.3f}V",
                    "value": cell_v,
                    "cell": i+1,
                    "threshold": 3.8
                })
                
        # 溫度警報檢查
        temperature = data.get("temperature")
        if temperature and temperature > 45:
            severity = "critical" if temperature > 55 else "warning"
            alerts.append({
                "type": "high_temperature",
                "severity": severity,
                "message": f"電池溫度過高: {temperature:.1f}°C",
                "value": temperature,
                "threshold": 45 if severity == "warning" else 55
            })
            
        # 發送警報
        for alert in alerts:
            alert["timestamp"] = datetime.now().isoformat()
            alert_payload = json.dumps(alert, ensure_ascii=False, indent=2)
            self.mqtt_client.publish(self.mqtt_topics["alerts"], alert_payload)
            logger.warning(f"發送警報: {alert['message']}")
            
    async def monitoring_loop(self):
        """主監控循環"""
        logger.info("開始 BMS 監控循環")
        
        while self.running:
            try:
                # 檢查連接狀態
                if not self.client or not self.client.is_connected:
                    logger.info("BMS 未連接，嘗試喚醒並連接...")
                    
                    # 喚醒 BMS
                    if not await self.bms_wake_attempt():
                        logger.error("BMS 喚醒失敗，等待重試...")
                        await asyncio.sleep(10)
                        continue
                        
                    # 連接 BMS  
                    if not await self.connect_bms():
                        logger.error("BMS 連接失敗，等待重試...")
                        await asyncio.sleep(10)
                        continue
                        
                # 讀取數據
                data = await self.read_bms_data()
                if data:
                    # 發送到 MQTT
                    await self.publish_mqtt_data(data)
                else:
                    logger.warning("BMS 數據讀取失敗")
                    
                # 發送系統狀態
                status_data = {
                    "timestamp": datetime.now().isoformat(),
                    "connected": self.client.is_connected if self.client else False,
                    "last_read": self.last_read_time,
                    "read_count": self.read_count,
                    "error_count": self.error_count,
                    "uptime": time.time() - self.start_time if hasattr(self, 'start_time') else 0
                }
                
                status_payload = json.dumps(status_data, ensure_ascii=False)
                self.mqtt_client.publish(self.mqtt_topics["status"], status_payload)
                
                # 等待下次讀取
                logger.debug("等待 30 秒後進行下次讀取...")
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"監控循環錯誤: {e}")
                self.error_count += 1
                await asyncio.sleep(5)  # 錯誤後短暫等待
                
    async def start(self):
        """啟動橋接程式"""
        logger.info("啟動 BMS-MQTT 橋接程式")
        
        # 設定 MQTT 連接
        if not self.setup_mqtt():
            logger.error("MQTT 設定失敗，程式結束")
            return
            
        self.start_time = time.time()
        self.running = True
        
        try:
            await self.monitoring_loop()
        except KeyboardInterrupt:
            logger.info("收到停止信號")
        finally:
            await self.stop()
            
    async def stop(self):
        """停止橋接程式"""
        logger.info("停止 BMS-MQTT 橋接程式")
        
        self.running = False
        
        # 斷開 BMS 連接
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            
        # 斷開 MQTT 連接
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        
        logger.info("橋接程式已停止")

async def main():
    """主程式"""
    print("🔋 BMS-MQTT 數據橋接程式")
    print("整合 DALY BMS D2 Modbus 與 Web 監控系統")
    print("=" * 50)
    
    bridge = BMSMQTTBridge()
    
    try:
        await bridge.start()
    except KeyboardInterrupt:
        print("\n程式被用戶中斷")
    except Exception as e:
        logger.error(f"程式執行錯誤: {e}")
        
if __name__ == "__main__":
    asyncio.run(main())