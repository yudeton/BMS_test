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

router = APIRouter()

# 假設我們有這些依賴注入
async def get_cache_service() -> CacheService:
    # 這將在主應用中實現
    pass

async def get_mqtt_service() -> MQTTService:
    # 這將在主應用中實現
    pass

@router.get("/health", response_model=HealthCheck)
async def health_check(
    cache: CacheService = Depends(get_cache_service),
    mqtt: MQTTService = Depends(get_mqtt_service)
):
    """健康檢查端點"""
    connections = {
        "mqtt": mqtt.is_connected() if mqtt else False,
        "redis": cache.is_connected() if cache else False,
        "database": True  # 簡化假設資料庫總是可用
    }
    
    return HealthCheck(
        timestamp=datetime.utcnow(),
        connections=connections
    )

@router.get("/realtime", response_model=BatteryRealtimeData)
async def get_realtime_data(cache: CacheService = Depends(get_cache_service)):
    """獲取即時電池數據"""
    try:
        # 首先嘗試從緩存獲取
        cached_data = await cache.get_latest_data("realtime")
        if cached_data:
            return BatteryRealtimeData(**cached_data)
        
        # 如果緩存沒有數據，返回預設值
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
async def get_history_data(duration: str, cache: CacheService = Depends(get_cache_service)):
    """獲取歷史數據"""
    try:
        duration_map = {
            '1h': timedelta(hours=1),
            '24h': timedelta(hours=24),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30)
        }
        
        time_delta = duration_map.get(duration, timedelta(hours=1))
        start_time = datetime.utcnow() - time_delta
        
        # 這裡需要實際的資料庫查詢，暫時返回空數據
        return {"data": [], "duration": duration, "start_time": start_time.isoformat()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history data: {str(e)}")

@router.get("/cells")
async def get_cell_data(cache: CacheService = Depends(get_cache_service)):
    """獲取電芯數據"""
    try:
        cached_data = await cache.get_latest_data("realtime")
        if cached_data and "cells" in cached_data:
            return {
                "cells": cached_data["cells"],
                "timestamp": cached_data.get("timestamp"),
                "count": len(cached_data["cells"])
            }
        
        return {"cells": [], "timestamp": None, "count": 0}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving cell data: {str(e)}")

@router.get("/alerts")
async def get_alerts(limit: int = 10, cache: CacheService = Depends(get_cache_service)):
    """獲取警報數據"""
    try:
        # 這裡需要實際的資料庫查詢，暫時返回空數據
        return {"alerts": [], "count": 0}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")

@router.get("/status", response_model=BatteryStatus)
async def get_system_status(cache: CacheService = Depends(get_cache_service)):
    """獲取系統狀態"""
    try:
        # 從緩存獲取系統狀態
        cached_status = await cache.get_latest_data("status")
        if cached_status:
            return BatteryStatus(**cached_status)
        
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
async def acknowledge_alert(alert_id: int):
    """確認警報"""
    try:
        # 這裡需要資料庫更新操作
        return {"message": f"Alert {alert_id} acknowledged", "alert_id": alert_id}
        
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