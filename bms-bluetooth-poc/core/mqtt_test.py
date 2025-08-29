#!/usr/bin/env python3

import json
import time
import paho.mqtt.client as mqtt
from datetime import datetime
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MQTTTester:
    def __init__(self):
        self.mqtt_broker = "localhost"
        self.mqtt_port = 1883
        self.mqtt_topics = {
            "realtime": "battery/realtime",
            "alerts": "battery/alerts",
            "status": "battery/status"
        }
        
        # 設置 MQTT 客戶端
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"MQTT 連接成功: {self.mqtt_broker}:{self.mqtt_port}")
        else:
            logger.error(f"MQTT 連接失敗，代碼: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        logger.info("MQTT 連接已斷開")
    
    def connect_mqtt(self):
        """連接到 MQTT 代理"""
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            logger.error(f"MQTT 連接錯誤: {e}")
            return False
    
    def create_test_data(self):
        """創建測試 BMS 數據 - 模擬 26.5V 8節電池"""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_voltage": 26.52,  # 總電壓 26.52V
            "current": -2.1,         # 放電電流 2.1A
            "power": -55.6,          # 放電功率 55.6W
            "soc": 85.2, # 電池電量百分比
            "temperature": 25.1,  # 平均溫度
            "cells": [         # 8節電池電壓
                3.315, 3.320, 3.318, 3.322,
                3.319, 3.317, 3.325, 3.314
            ],
            "cell_balance": [True, True, False, True, True, True, False, True],
            "protection_status": {
                "overvoltage": False,
                "undervoltage": False,
                "overcurrent_charge": False,
                "overcurrent_discharge": False,
                "overtemperature": False,
                "undertemperature": False
            },
            "cycle_count": 127,
            "soc": 85.2,            # 電量百分比
            "soh": 98.5             # 健康度
        }
    
    def publish_test_data(self):
        """發布測試數據到 MQTT"""
        try:
            # 發布即時數據
            realtime_data = self.create_test_data()
            self.mqtt_client.publish(
                self.mqtt_topics["realtime"], 
                json.dumps(realtime_data, ensure_ascii=False)
            )
            logger.info("發布即時數據到 MQTT")
            
            # 發布狀態數據
            status_data = {
                "timestamp": datetime.now().isoformat(),
                "connected": True,
                "device_id": "DALY-BMS-TEST",
                "firmware_version": "1.0.0",
                "last_update": datetime.now().isoformat()
            }
            self.mqtt_client.publish(
                self.mqtt_topics["status"], 
                json.dumps(status_data, ensure_ascii=False)
            )
            logger.info("發布狀態數據到 MQTT")
            
            # 檢查是否有警報
            if realtime_data["total_voltage"] > 29.0:
                alert_data = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "overvoltage",
                    "severity": "warning",
                    "message": f"電壓過高: {realtime_data['total_voltage']}V"
                }
                self.mqtt_client.publish(
                    self.mqtt_topics["alerts"], 
                    json.dumps(alert_data, ensure_ascii=False)
                )
                logger.warning("發布警報數據到 MQTT")
                
        except Exception as e:
            logger.error(f"發布數據失敗: {e}")
    
    def run_test(self, duration=30):
        """運行測試，持續發送數據"""
        logger.info("開始 MQTT 測試")
        
        if not self.connect_mqtt():
            logger.error("無法連接 MQTT，測試終止")
            return
        
        start_time = time.time()
        counter = 0
        
        try:
            while time.time() - start_time < duration:
                self.publish_test_data()
                counter += 1
                logger.info(f"已發送 {counter} 組測試數據")
                time.sleep(5)  # 每5秒發送一次
                
        except KeyboardInterrupt:
            logger.info("收到中斷信號，停止測試")
        finally:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("MQTT 測試結束")

if __name__ == "__main__":
    tester = MQTTTester()
    print("開始 BMS MQTT 測試 (30秒)")
    print("模擬 DALY BMS 數據: 26.5V, 8節電池")
    print("按 Ctrl+C 提前結束測試")
    tester.run_test(30)