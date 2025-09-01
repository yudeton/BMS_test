from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from typing import List, Optional
from datetime import datetime, timedelta
import json

from ..models.database import BatteryData, BatteryAlert, SystemStatus
from ..models.schemas import BatteryRealtimeData, BatteryAlert as AlertSchema, BatteryStatus, HealthCheck
from ..services.cache_service import CacheService
from ..services.mqtt_service import MQTTService
from ..services.database_service import DatabaseService
from ..services.bms_service import BMSService

router = APIRouter()

@router.get("/status")
async def get_system_status():
    """系統狀態端點"""
    try:
        return {
            "status": "ok",
            "database": "connected",
            "timestamp": datetime.now().isoformat(),
            "bms": "monitoring",
            "message": "Enhanced BMS monitoring system with POC integration active",
            "features": [
                "D2 Modbus protocol support",
                "PostgreSQL data persistence",
                "Real-time WebSocket updates",
                "Alert management",
                "Historical data queries"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System error: {str(e)}")

# 假設我們有這些依賴注入
async def get_cache_service() -> CacheService:
    # 這將在主應用中實現
    pass

async def get_mqtt_service() -> MQTTService:
    # 這將在主應用中實現
    pass

async def get_database_service() -> DatabaseService:
    # 這將在主應用中實現
    pass

async def get_bms_service() -> BMSService:
    # 這將在主應用中實現
    pass

@router.get("/health", response_model=HealthCheck)
async def health_check(
    cache: CacheService = Depends(get_cache_service),
    mqtt: MQTTService = Depends(get_mqtt_service),
    database: DatabaseService = Depends(get_database_service)
):
    """健康檢查端點（增強版）"""
    connections = {
        "database": database.is_connected() if database else False,
        "redis": cache.is_connected() if cache else False,
        "mqtt": mqtt.is_connected() if mqtt else False
    }
    
    return HealthCheck(
        timestamp=datetime.utcnow(),
        connections=connections
    )

@router.get("/diagnostics/soc-candidates")
async def diag_soc_candidates(
    bms: BMSService = Depends(get_bms_service)
):
    """診斷：掃描可能的 SOC 寄存器（根源定位用）。"""
    try:
        if not bms.connected:
            ok = await bms.connect()
            if not ok:
                return {"error": "BMS not connected"}

        # 讀取大範圍數據
        cmd = bms.build_modbus_command(0x0000, 0x003E)
        responses = await bms.send_command(cmd, 4.0, "診斷大範圍讀取")
        for response in responses:
            if response == cmd:
                continue
            # 擷取 payload
            if len(response) < 5:
                continue
            data_len = response[2]
            payload = response[3:3+data_len]
            cands = []
            for reg in range(0x20, 0x40):
                pos = reg*2
                if pos+1 < len(payload):
                    raw = int.from_bytes(payload[pos:pos+2], 'big')
                    val = raw * bms.soc_scale + bms.soc_offset
                    if 0.0 <= val <= 100.0:
                        cands.append({"register": f"0x{reg:02X}", "raw": raw, "val": round(val,1), "selected": (reg == bms.registers["soc"])})
            return {"candidates": cands, "using": f"0x{bms.registers['soc']:02X}", "scale": bms.soc_scale, "offset": bms.soc_offset}
        return {"error": "no valid response"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime", response_model=BatteryRealtimeData)
async def get_realtime_data(
    cache: CacheService = Depends(get_cache_service),
    database: DatabaseService = Depends(get_database_service)
):
    """獲取即時電池數據（增強版）"""
    try:
        # 首先嘗試從緩存獲取（最快）
        if cache and cache.is_connected():
            cached_data = await cache.get_latest_data("realtime")
            if cached_data:
                return BatteryRealtimeData(**cached_data)
        
        # 如果緩存未命中，從資料庫獲取最新數據
        if database and database.is_connected():
            latest_data = await database.get_latest_battery_data(limit=1)
            if latest_data:
                data = latest_data[0]
                return BatteryRealtimeData(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    total_voltage=data.get("total_voltage", 0.0),
                    current=data.get("current", 0.0),
                    power=data.get("power", 0.0),
                    soc=data.get("soc", 0.0),
                    temperature=data.get("temperature", 0.0),
                    status=data.get("status", "unknown"),
                    connection_status=data.get("connection_status", "disconnected")
                )
        
        # 如果沒有數據，返回預設值
        return BatteryRealtimeData(
            timestamp=datetime.utcnow(),
            total_voltage=0.0,
            current=0.0,
            power=0.0,
            soc=0.0,
            temperature=0.0,
            status="no_data",
            connection_status="disconnected"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving realtime data: {str(e)}")

@router.get("/history/{duration}")
async def get_history_data(
    duration: str, 
    database: DatabaseService = Depends(get_database_service)
):
    """獲取歷史數據（實現版）"""
    try:
        duration_map = {
            '1h': 1,
            '24h': 24,
            '7d': 24 * 7,
            '30d': 24 * 30
        }
        
        hours = duration_map.get(duration, 1)
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # 從資料庫獲取歷史數據
        if database and database.is_connected():
            history_data = await database.get_battery_history(hours=hours)
            return {
                "data": history_data, 
                "duration": duration, 
                "start_time": start_time.isoformat(),
                "count": len(history_data)
            }
        else:
            return {
                "data": [], 
                "duration": duration, 
                "start_time": start_time.isoformat(),
                "count": 0,
                "error": "Database not connected"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history data: {str(e)}")

@router.get("/cells")
async def get_cell_data(
    cache: CacheService = Depends(get_cache_service),
    database: DatabaseService = Depends(get_database_service)
):
    """獲取電芯數據（增強版）"""
    try:
        # 先嘗試從緩存獲取
        if cache and cache.is_connected():
            cached_data = await cache.get_latest_data("realtime")
            if cached_data and "cells" in cached_data:
                return {
                    "cells": cached_data["cells"],
                    "timestamp": cached_data.get("timestamp"),
                    "count": len(cached_data["cells"])
                }
        
        # 從資料庫獲取最新數據
        if database and database.is_connected():
            latest_data = await database.get_latest_battery_data(limit=1)
            if latest_data:
                data = latest_data[0]
                cells = data.get("cells", [])
                return {
                    "cells": cells,
                    "timestamp": data.get("timestamp"),
                    "count": len(cells)
                }
        
        return {"cells": [], "timestamp": None, "count": 0}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving cell data: {str(e)}")

@router.get("/alerts")
async def get_alerts(
    limit: int = 10, 
    database: DatabaseService = Depends(get_database_service)
):
    """獲取警報數據（實現版）"""
    try:
        if database and database.is_connected():
            alerts = await database.get_active_alerts(limit=limit)
            return {"alerts": alerts, "count": len(alerts)}
        else:
            return {"alerts": [], "count": 0, "error": "Database not connected"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")

@router.get("/system-status", response_model=BatteryStatus)
async def get_system_status(
    cache: CacheService = Depends(get_cache_service),
    database: DatabaseService = Depends(get_database_service)
):
    """獲取系統狀態（增強版）"""
    try:
        # 先嘗試從緩存獲取
        if cache and cache.is_connected():
            cached_status = await cache.get_latest_data("status")
            if cached_status:
                return BatteryStatus(**cached_status)
        
        # TODO: 從資料庫獲取最新系統狀態
        
        # 預設狀態
        return BatteryStatus(
            timestamp=datetime.utcnow(),
            connected=False,
            read_count=0,
            error_count=0,
            uptime=0.0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving system status: {str(e)}")

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    database: DatabaseService = Depends(get_database_service)
):
    """確認警報（實現版）"""
    try:
        if database and database.is_connected():
            success = await database.acknowledge_alert(alert_id)
            if success:
                return {"message": f"Alert {alert_id} acknowledged successfully", "alert_id": alert_id}
            else:
                raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        else:
            raise HTTPException(status_code=503, detail="Database not available")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error acknowledging alert: {str(e)}")

# 測試用端點
@router.get("/test")
async def test_endpoint():
    """測試端點"""
    return {
        "message": "FastAPI BMS Monitor API is running!",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
