import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import paho.mqtt.client as mqtt_client
from asyncio_mqtt import Client as AsyncMQTTClient

logger = logging.getLogger(__name__)

class MQTTService:
    """MQTT 服務"""
    
    def __init__(self, broker_url: str = "mqtt://localhost:1883", client_id: str = "fastapi-battery-monitor"):
        self.broker_url = broker_url
        self.client_id = client_id
        self.client: Optional[AsyncMQTTClient] = None
        self.connected = False
        self.message_handlers: Dict[str, Callable] = {}
        self.topics = {
            "realtime": "battery/realtime",
            "alerts": "battery/alerts", 
            "status": "battery/status",
            "cells": "battery/cells"
        }
    
    async def connect(self):
        """連接到 MQTT Broker"""
        try:
            # 解析 broker URL
            if self.broker_url.startswith("mqtt://"):
                host = self.broker_url.replace("mqtt://", "").split(":")[0]
                port = int(self.broker_url.split(":")[-1]) if ":" in self.broker_url.replace("mqtt://", "") else 1883
            else:
                host = "localhost"
                port = 1883
            
            self.client = AsyncMQTTClient(hostname=host, port=port, client_id=self.client_id)
            await self.client.connect()
            self.connected = True
            logger.info(f"MQTT 已連接到 {host}:{port}")
            
            # 訂閱主題
            await self.subscribe_topics()
            
        except Exception as e:
            logger.error(f"MQTT 連接失敗: {e}")
            self.connected = False
            raise
    
    async def disconnect(self):
        """斷開 MQTT 連接"""
        if self.client:
            await self.client.disconnect()
            self.connected = False
            logger.info("MQTT 已斷開連接")
    
    def is_connected(self) -> bool:
        """檢查連接狀態"""
        return self.connected
    
    async def subscribe_topics(self):
        """訂閱主題"""
        if not self.connected:
            return
        
        try:
            for topic_name, topic in self.topics.items():
                await self.client.subscribe(topic)
                logger.info(f"已訂閱 MQTT 主題: {topic}")
        except Exception as e:
            logger.error(f"訂閱主題失敗: {e}")
    
    async def publish(self, topic: str, message: Dict[str, Any]):
        """發布消息"""
        if not self.connected:
            logger.warning("MQTT 未連接，無法發布消息")
            return False
        
        try:
            payload = json.dumps(message, default=str)
            await self.client.publish(topic, payload)
            logger.debug(f"已發布消息到 {topic}: {payload[:100]}...")
            return True
        except Exception as e:
            logger.error(f"發布消息失敗: {e}")
            return False
    
    async def publish_realtime_data(self, data: Dict[str, Any]):
        """發布即時數據"""
        return await self.publish(self.topics["realtime"], data)
    
    async def publish_alert(self, alert: Dict[str, Any]):
        """發布警報"""
        return await self.publish(self.topics["alerts"], alert)
    
    async def publish_status(self, status: Dict[str, Any]):
        """發布狀態"""
        return await self.publish(self.topics["status"], status)
    
    def register_message_handler(self, topic: str, handler: Callable):
        """註冊消息處理器"""
        self.message_handlers[topic] = handler
        logger.info(f"已註冊消息處理器: {topic}")
    
    async def start_listening(self):
        """開始監聽消息"""
        if not self.connected:
            logger.warning("MQTT 未連接，無法開始監聽")
            return
        
        try:
            async with self.client.messages() as messages:
                async for message in messages:
                    await self.handle_message(message)
        except Exception as e:
            logger.error(f"MQTT 消息監聽錯誤: {e}")
    
    async def handle_message(self, message):
        """處理接收到的消息"""
        try:
            topic = str(message.topic)
            payload = message.payload.decode()
            
            logger.debug(f"收到 MQTT 消息: {topic} - {payload[:100]}...")
            
            # 解析 JSON 數據
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning(f"無法解析 JSON 消息: {payload[:100]}...")
                return
            
            # 調用註冊的處理器
            if topic in self.message_handlers:
                await self.message_handlers[topic](topic, data)
            else:
                # 預設處理
                await self.default_message_handler(topic, data)
                
        except Exception as e:
            logger.error(f"處理消息錯誤: {e}")
    
    async def default_message_handler(self, topic: str, data: Dict[str, Any]):
        """預設消息處理器"""
        logger.info(f"收到消息 - 主題: {topic}, 數據類型: {type(data)}")
        
        # 這裡可以添加預設的數據處理邏輯
        # 例如：儲存到緩存、觸發 WebSocket 廣播等
    
    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        return {
            "connected": self.connected,
            "client_id": self.client_id,
            "broker_url": self.broker_url,
            "subscribed_topics": list(self.topics.values()),
            "timestamp": datetime.utcnow().isoformat()
        }