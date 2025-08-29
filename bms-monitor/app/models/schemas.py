from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BatteryRealtimeData(BaseModel):
    """即時電池數據模型"""
    timestamp: datetime
    total_voltage: Optional[float] = None
    current: Optional[float] = None
    power: Optional[float] = None
    soc: Optional[float] = None
    temperature: Optional[float] = None
    status: str = "unknown"
    cells: List[float] = []
    temperatures: List[float] = []
    connection_status: str = "disconnected"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BatteryAlert(BaseModel):
    """電池警報模型"""
    timestamp: datetime
    type: str
    severity: str  # warning, critical
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None
    cell: Optional[int] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BatteryStatus(BaseModel):
    """電池狀態模型"""
    timestamp: datetime
    connected: bool
    last_read: Optional[datetime] = None
    read_count: int = 0
    error_count: int = 0
    uptime: float = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class HealthCheck(BaseModel):
    """健康檢查模型"""
    status: str = "healthy"
    timestamp: datetime
    connections: dict
    version: str = "1.0.0"

class BMSDataMessage(BaseModel):
    """MQTT BMS 數據消息模型"""
    timestamp: str
    voltage: Optional[float] = None
    current: Optional[float] = None
    power: Optional[float] = None
    soc: Optional[float] = None
    temperature: Optional[float] = None
    status: str = "normal"
    cells: List[float] = []
    temperatures: List[float] = []
    metadata: Optional[dict] = None