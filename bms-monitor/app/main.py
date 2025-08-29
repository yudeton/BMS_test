from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from .config import settings
from .api.routes import router as api_router
from .api.websocket import websocket_endpoint, websocket_manager, start_heartbeat_task
from .services.cache_service import CacheService
from .services.mqtt_service import MQTTService
from .services.bms_service import BMSService
from .services.database_service import DatabaseService

# 設置日誌
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局服務實例
cache_service = CacheService(settings.redis_url)
mqtt_service = MQTTService(settings.mqtt_broker_url, settings.mqtt_client_id)
bms_service = BMSService(settings.bms_mac_address)
database_service = DatabaseService(settings.database_url)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時
    logger.info("🚀 啟動 FastAPI BMS 監控服務...")
    
    # 連接服務
    try:
        await database_service.initialize()
        logger.info("✅ 資料庫服務已連接")
    except Exception as e:
        logger.error(f"❌ 資料庫服務連接失敗: {e}")
        # 資料庫是關鍵服務，失敗則拋出異常
        raise
    
    try:
        await cache_service.connect()
        logger.info("✅ Redis 緩存服務已連接")
    except Exception as e:
        logger.warning(f"⚠️  Redis 緩存服務連接失敗: {e}")
    
    try:
        await mqtt_service.connect()
        logger.info("✅ MQTT 服務已連接")
        
        # 註冊 MQTT 消息處理器
        mqtt_service.register_message_handler(
            mqtt_service.topics["realtime"], 
            handle_realtime_data
        )
        mqtt_service.register_message_handler(
            mqtt_service.topics["alerts"], 
            handle_alert_data
        )
        
    except Exception as e:
        logger.warning(f"⚠️  MQTT 服務連接失敗: {e}")
    
    # 啟動後台任務
    asyncio.create_task(bms_monitoring_task())
    asyncio.create_task(start_heartbeat_task())
    
    if mqtt_service.is_connected():
        asyncio.create_task(mqtt_service.start_listening())
    
    logger.info("🎉 FastAPI BMS 監控服務啟動完成")
    
    yield
    
    # 關閉時
    logger.info("🔄 正在關閉服務...")
    await cache_service.disconnect()
    await mqtt_service.disconnect()
    await bms_service.disconnect()
    await database_service.close()
    logger.info("✅ 服務已關閉")

app = FastAPI(
    title="BMS 監控系統",
    description="基於 FastAPI 的電池管理系統監控服務",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 依賴注入
async def get_cache_service() -> CacheService:
    return cache_service

async def get_mqtt_service() -> MQTTService:
    return mqtt_service

async def get_bms_service() -> BMSService:
    return bms_service

async def get_database_service() -> DatabaseService:
    return database_service

# 更新路由中的依賴注入
app.dependency_overrides[get_cache_service] = lambda: cache_service
app.dependency_overrides[get_mqtt_service] = lambda: mqtt_service
app.dependency_overrides[get_database_service] = lambda: database_service

# 註冊路由
app.include_router(api_router, prefix="/api")

# WebSocket 端點
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await websocket_endpoint(websocket)

# 靜態文件（如果需要）
# app.mount("/", StaticFiles(directory="static", html=True), name="static")

# 根路徑
@app.get("/")
async def root():
    return {
        "message": "BMS 監控系統 FastAPI 服務",
        "version": "1.0.0",
        "status": "running",
        "services": {
            "database": database_service.is_connected(),
            "cache": cache_service.is_connected(),
            "mqtt": mqtt_service.is_connected(),
            "bms": bms_service.connected
        }
    }

async def handle_realtime_data(topic: str, data: Dict[str, Any]):
    """處理即時數據消息（增強版）"""
    try:
        # 儲存到資料庫（持久化）
        if database_service.is_connected():
            data_id = await database_service.save_battery_data(data)
            if data_id:
                logger.debug(f"電池數據已儲存到資料庫，ID: {data_id}")
        
        # 存儲到緩存（即時訪問）
        if cache_service.is_connected():
            await cache_service.set_latest_data("realtime", data)
        
        # 廣播到 WebSocket 客戶端
        await websocket_manager.broadcast(data, "realtime")
        
        logger.debug(f"處理即時數據: {topic} - 電壓: {data.get('total_voltage', 'N/A')}V, 電流: {data.get('current', 'N/A')}A")
        
    except Exception as e:
        logger.error(f"處理即時數據錯誤: {e}")

async def handle_alert_data(topic: str, data: Dict[str, Any]):
    """處理警報數據消息（增強版）"""
    try:
        # 儲存警報到資料庫
        if database_service.is_connected():
            alert_id = await database_service.save_battery_alert(
                alert_type=data.get("type", "unknown"),
                severity=data.get("severity", "info"),
                message=data.get("message", ""),
                value=data.get("value"),
                threshold=data.get("threshold"),
                cell=data.get("cell")
            )
            if alert_id:
                logger.info(f"警報已儲存到資料庫，ID: {alert_id}")
        
        # 廣播警報到 WebSocket 客戶端
        await websocket_manager.broadcast(data, "alerts")
        
        logger.warning(f"🚨 警報: {data.get('message', 'Unknown alert')} (等級: {data.get('severity', 'unknown')})")
        
    except Exception as e:
        logger.error(f"處理警報數據錯誤: {e}")

async def bms_monitoring_task():
    """BMS 監控後台任務"""
    logger.info("🔋 BMS 監控任務啟動")
    
    while True:
        try:
            # 嘗試連接 BMS
            if not bms_service.connected:
                logger.info("🔌 嘗試連接 BMS...")
                if await bms_service.connect():
                    logger.info("✅ BMS 連接成功，正在喚醒設備...")
                    await bms_service.wake_bms()
                else:
                    logger.warning("❌ BMS 連接失敗，30秒後重試")
                    await asyncio.sleep(30)
                    continue
            
            # 讀取 BMS 數據
            data = await bms_service.read_bms_data()
            if data:
                # 發布到 MQTT
                if mqtt_service.is_connected():
                    await mqtt_service.publish_realtime_data(data)
                
                # 直接處理數據（如果 MQTT 未連接）
                if not mqtt_service.is_connected():
                    await handle_realtime_data("direct", data)
                
                # 檢查警報
                alerts = check_alerts(data)
                for alert in alerts:
                    if mqtt_service.is_connected():
                        await mqtt_service.publish_alert(alert)
                    else:
                        await handle_alert_data("direct", alert)
            
            # 等待下次讀取
            await asyncio.sleep(settings.bms_read_interval)
            
        except Exception as e:
            logger.error(f"BMS 監控任務錯誤: {e}")
            await asyncio.sleep(10)

def check_alerts(data: Dict[str, Any]) -> list:
    """檢查警報條件"""
    alerts = []
    
    try:
        # 電壓警報
        voltage = data.get("total_voltage")
        if voltage:
            if voltage < 24.0:
                alerts.append({
                    "timestamp": data.get("timestamp"),
                    "type": "voltage",
                    "severity": "critical",
                    "message": f"總電壓過低: {voltage:.1f}V",
                    "value": voltage,
                    "threshold": 24.0
                })
            elif voltage > 30.4:
                alerts.append({
                    "timestamp": data.get("timestamp"),
                    "type": "voltage",
                    "severity": "critical", 
                    "message": f"總電壓過高: {voltage:.1f}V",
                    "value": voltage,
                    "threshold": 30.4
                })
        
        # 電芯電壓警報
        cells = data.get("cells", [])
        for i, cell_v in enumerate(cells):
            if cell_v < 3.0:
                alerts.append({
                    "timestamp": data.get("timestamp"),
                    "type": "cell_voltage",
                    "severity": "critical",
                    "message": f"電芯 {i+1} 電壓過低: {cell_v:.3f}V",
                    "value": cell_v,
                    "cell": i+1,
                    "threshold": 3.0
                })
        
        # 溫度警報
        temperature = data.get("temperature")
        if temperature and temperature > 45:
            severity = "critical" if temperature > 55 else "warning"
            alerts.append({
                "timestamp": data.get("timestamp"),
                "type": "temperature",
                "severity": severity,
                "message": f"溫度過高: {temperature:.1f}°C",
                "value": temperature,
                "threshold": 45 if severity == "warning" else 55
            })
    
    except Exception as e:
        logger.error(f"檢查警報錯誤: {e}")
    
    return alerts

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )