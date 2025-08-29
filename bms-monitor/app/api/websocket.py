from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket 連接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_info: Dict[WebSocket, dict] = {}
    
    async def connect(self, websocket: WebSocket, client_ip: str = None):
        """接受新的 WebSocket 連接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_info[websocket] = {
            "connected_at": datetime.utcnow(),
            "client_ip": client_ip,
            "last_ping": datetime.utcnow()
        }
        logger.info(f"WebSocket 客戶端已連接: {client_ip}, 總連接數: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """斷開 WebSocket 連接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.client_info:
            del self.client_info[websocket]
        logger.info(f"WebSocket 客戶端已斷開，總連接數: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """發送個人消息"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"發送個人消息失敗: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, data: dict, topic: str = "realtime"):
        """廣播消息給所有連接的客戶端"""
        if not self.active_connections:
            return
        
        message = {
            "topic": topic,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"廣播消息失敗: {e}")
                disconnected.append(connection)
        
        # 清理失效連接
        for conn in disconnected:
            self.disconnect(conn)
    
    def get_connected_clients(self) -> int:
        """獲取連接數量"""
        return len(self.active_connections)
    
    def get_client_info(self) -> List[dict]:
        """獲取客戶端信息"""
        return [
            {
                "connected_at": info["connected_at"].isoformat(),
                "client_ip": info["client_ip"],
                "last_ping": info["last_ping"].isoformat()
            }
            for info in self.client_info.values()
        ]
    
    async def send_heartbeat(self):
        """發送心跳檢測"""
        heartbeat_message = {
            "type": "heartbeat",
            "timestamp": datetime.utcnow().isoformat(),
            "server_time": datetime.utcnow().timestamp()
        }
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(heartbeat_message))
            except Exception:
                disconnected.append(connection)
        
        # 清理失效連接
        for conn in disconnected:
            self.disconnect(conn)

# 全局 WebSocket 管理器實例
websocket_manager = WebSocketManager()

async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端點處理函數"""
    client_ip = websocket.client.host if websocket.client else "unknown"
    await websocket_manager.connect(websocket, client_ip)
    
    try:
        # 發送歡迎消息
        welcome_message = {
            "type": "welcome",
            "message": "已連接到 BMS 監控 WebSocket",
            "timestamp": datetime.utcnow().isoformat(),
            "client_count": websocket_manager.get_connected_clients()
        }
        await websocket_manager.send_personal_message(welcome_message, websocket)
        
        while True:
            try:
                # 等待客戶端消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 處理不同類型的消息
                if message.get("type") == "ping":
                    # 更新最後 ping 時間
                    if websocket in websocket_manager.client_info:
                        websocket_manager.client_info[websocket]["last_ping"] = datetime.utcnow()
                    
                    # 回覆 pong
                    pong_message = {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket_manager.send_personal_message(pong_message, websocket)
                
                elif message.get("type") == "subscribe":
                    # 處理訂閱請求
                    topics = message.get("topics", [])
                    response = {
                        "type": "subscription_confirmed",
                        "topics": topics,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket_manager.send_personal_message(response, websocket)
                
            except asyncio.TimeoutError:
                # 定期發送心跳
                continue
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket 客戶端主動斷開: {client_ip}")
    except Exception as e:
        logger.error(f"WebSocket 錯誤: {e}")
    finally:
        websocket_manager.disconnect(websocket)

async def start_heartbeat_task():
    """啟動心跳任務"""
    while True:
        await asyncio.sleep(30)  # 每30秒發送一次心跳
        await websocket_manager.send_heartbeat()