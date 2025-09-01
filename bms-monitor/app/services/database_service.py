import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from ..models.database import BatteryData, BatteryAlert, SystemStatus

logger = logging.getLogger(__name__)

class DatabaseService:
    """資料庫服務 - 處理 BMS 數據的持久化"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.async_session_maker = None
        self.connected = False
    
    async def initialize(self):
        """初始化資料庫連接"""
        try:
            # 創建異步引擎
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            # 創建會話工廠
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # 測試連接
            async with self.async_session_maker() as session:
                await session.execute(select(1))
                await session.commit()
            
            self.connected = True
            logger.info("資料庫服務初始化成功")
            
        except Exception as e:
            logger.error(f"資料庫初始化失敗: {e}")
            self.connected = False
            raise
    
    async def close(self):
        """關閉資料庫連接"""
        if self.engine:
            await self.engine.dispose()
        self.connected = False
        logger.info("資料庫連接已關閉")
    
    async def save_battery_data(self, data: Dict[str, Any]) -> Optional[int]:
        """儲存電池數據到資料庫"""
        if not self.connected:
            logger.warning("資料庫未連接，無法儲存數據")
            return None
        
        try:
            async with self.async_session_maker() as session:
                # 準備數據
                battery_data = BatteryData(
                    timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
                    total_voltage=data.get("total_voltage"),
                    current=data.get("current"),
                    power=data.get("power"),
                    soc=data.get("soc"),
                    temperature=data.get("temperature"),
                    status=data.get("status", "unknown"),
                    cells=json.dumps(data.get("cells", [])) if data.get("cells") else None,
                    temperatures=json.dumps(data.get("temperatures", [])) if data.get("temperatures") else None,
                    connection_status=data.get("connection_status", "unknown")
                )
                
                session.add(battery_data)
                await session.commit()
                await session.refresh(battery_data)
                
                logger.debug(f"電池數據已儲存，ID: {battery_data.id}")
                return battery_data.id
                
        except SQLAlchemyError as e:
            logger.error(f"儲存電池數據失敗: {e}")
            return None
    
    async def save_battery_alert(self, alert_type: str, severity: str, message: str, 
                               value: Optional[float] = None, threshold: Optional[float] = None,
                               cell: Optional[int] = None) -> Optional[int]:
        """儲存電池警報"""
        if not self.connected:
            logger.warning("資料庫未連接，無法儲存警報")
            return None
        
        try:
            async with self.async_session_maker() as session:
                alert = BatteryAlert(
                    timestamp=datetime.utcnow(),
                    type=alert_type,
                    severity=severity,
                    message=message,
                    value=value,
                    threshold=threshold,
                    cell=cell,
                    acknowledged=False
                )
                
                session.add(alert)
                await session.commit()
                await session.refresh(alert)
                
                logger.info(f"警報已儲存: {alert_type} - {message}")
                return alert.id
                
        except SQLAlchemyError as e:
            logger.error(f"儲存警報失敗: {e}")
            return None
    
    async def update_system_status(self, connected: bool, read_count: int, 
                                 error_count: int, uptime: float) -> Optional[int]:
        """更新系統狀態"""
        if not self.connected:
            logger.warning("資料庫未連接，無法更新狀態")
            return None
        
        try:
            async with self.async_session_maker() as session:
                status = SystemStatus(
                    timestamp=datetime.utcnow(),
                    connected=connected,
                    last_read=datetime.utcnow() if connected else None,
                    read_count=read_count,
                    error_count=error_count,
                    uptime=uptime
                )
                
                session.add(status)
                await session.commit()
                await session.refresh(status)
                
                logger.debug(f"系統狀態已更新，ID: {status.id}")
                return status.id
                
        except SQLAlchemyError as e:
            logger.error(f"更新系統狀態失敗: {e}")
            return None
    
    async def get_latest_battery_data(self, limit: int = 1) -> List[Dict[str, Any]]:
        """獲取最新的電池數據"""
        if not self.connected:
            return []
        
        try:
            async with self.async_session_maker() as session:
                stmt = (
                    select(BatteryData)
                    .order_by(BatteryData.timestamp.desc())
                    .limit(limit)
                )
                result = await session.execute(stmt)
                battery_data_list = result.scalars().all()
                
                return [
                    {
                        "id": bd.id,
                        "timestamp": bd.timestamp.isoformat(),
                        "total_voltage": bd.total_voltage,
                        "current": bd.current,
                        "power": bd.power,
                        "soc": bd.soc,
                        "temperature": bd.temperature,
                        "status": bd.status,
                        "cells": json.loads(bd.cells) if bd.cells else [],
                        "temperatures": json.loads(bd.temperatures) if bd.temperatures else [],
                        "connection_status": bd.connection_status
                    }
                    for bd in battery_data_list
                ]
                
        except SQLAlchemyError as e:
            logger.error(f"獲取電池數據失敗: {e}")
            return []
    
    async def get_battery_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """獲取電池歷史數據"""
        if not self.connected:
            return []
        
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            async with self.async_session_maker() as session:
                stmt = (
                    select(BatteryData)
                    .where(BatteryData.timestamp >= since)
                    .order_by(BatteryData.timestamp.desc())
                    .limit(1000)  # 限制最大返回數量
                )
                result = await session.execute(stmt)
                battery_data_list = result.scalars().all()
                
                return [
                    {
                        "timestamp": bd.timestamp.isoformat(),
                        "total_voltage": bd.total_voltage,
                        "current": bd.current,
                        "power": bd.power,
                        "soc": bd.soc,
                        "temperature": bd.temperature,
                        "temperatures": json.loads(bd.temperatures) if bd.temperatures else [],
                        "cells": json.loads(bd.cells) if bd.cells else [],
                        "status": bd.status,
                        "connection_status": bd.connection_status
                    }
                    for bd in battery_data_list
                ]
                
        except SQLAlchemyError as e:
            logger.error(f"獲取歷史數據失敗: {e}")
            return []
    
    async def get_active_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取活動警報"""
        if not self.connected:
            return []
        
        try:
            async with self.async_session_maker() as session:
                stmt = (
                    select(BatteryAlert)
                    .where(BatteryAlert.acknowledged == False)
                    .order_by(BatteryAlert.timestamp.desc())
                    .limit(limit)
                )
                result = await session.execute(stmt)
                alerts = result.scalars().all()
                
                return [
                    {
                        "id": alert.id,
                        "timestamp": alert.timestamp.isoformat(),
                        "type": alert.type,
                        "severity": alert.severity,
                        "message": alert.message,
                        "value": alert.value,
                        "threshold": alert.threshold,
                        "cell": alert.cell,
                        "acknowledged": alert.acknowledged
                    }
                    for alert in alerts
                ]
                
        except SQLAlchemyError as e:
            logger.error(f"獲取警報失敗: {e}")
            return []
    
    async def acknowledge_alert(self, alert_id: int) -> bool:
        """確認警報"""
        if not self.connected:
            return False
        
        try:
            async with self.async_session_maker() as session:
                stmt = select(BatteryAlert).where(BatteryAlert.id == alert_id)
                result = await session.execute(stmt)
                alert = result.scalar_one_or_none()
                
                if alert:
                    alert.acknowledged = True
                    await session.commit()
                    logger.info(f"警報 {alert_id} 已確認")
                    return True
                else:
                    logger.warning(f"警報 {alert_id} 不存在")
                    return False
                    
        except SQLAlchemyError as e:
            logger.error(f"確認警報失敗: {e}")
            return False
    
    async def cleanup_old_data(self, keep_days: int = 30):
        """清理舊數據"""
        if not self.connected:
            return
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
            
            async with self.async_session_maker() as session:
                # 清理舊的電池數據
                stmt = select(BatteryData).where(BatteryData.timestamp < cutoff_date)
                result = await session.execute(stmt)
                old_battery_data = result.scalars().all()
                
                for data in old_battery_data:
                    await session.delete(data)
                
                # 清理舊的系統狀態
                stmt = select(SystemStatus).where(SystemStatus.timestamp < cutoff_date)
                result = await session.execute(stmt)
                old_status_data = result.scalars().all()
                
                for status in old_status_data:
                    await session.delete(status)
                
                await session.commit()
                logger.info(f"已清理 {len(old_battery_data)} 條電池數據和 {len(old_status_data)} 條系統狀態")
                
        except SQLAlchemyError as e:
            logger.error(f"清理舊數據失敗: {e}")
    
    def is_connected(self) -> bool:
        """檢查資料庫連接狀態"""
        return self.connected
