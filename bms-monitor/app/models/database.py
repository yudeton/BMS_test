from sqlalchemy import Column, Integer, Float, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime
import json

Base = declarative_base()

class BatteryData(Base):
    """電池數據表"""
    __tablename__ = "battery_data"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    total_voltage = Column(Float, nullable=True)
    current = Column(Float, nullable=True)
    power = Column(Float, nullable=True)
    soc = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    status = Column(String(50), default="unknown")
    cells = Column(Text, nullable=True)  # JSON string
    temperatures = Column(Text, nullable=True)  # JSON string
    connection_status = Column(String(50), default="disconnected")
    
    def to_dict(self):
        """轉換為字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "total_voltage": self.total_voltage,
            "current": self.current,
            "power": self.power,
            "soc": self.soc,
            "temperature": self.temperature,
            "status": self.status,
            "cells": json.loads(self.cells) if self.cells else [],
            "temperatures": json.loads(self.temperatures) if self.temperatures else [],
            "connection_status": self.connection_status
        }

class BatteryAlert(Base):
    """電池警報表"""
    __tablename__ = "battery_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    value = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    cell = Column(Integer, nullable=True)
    acknowledged = Column(Boolean, default=False)
    
    def to_dict(self):
        """轉換為字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "type": self.type,
            "severity": self.severity,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "cell": self.cell,
            "acknowledged": self.acknowledged
        }

class SystemStatus(Base):
    """系統狀態表"""
    __tablename__ = "system_status"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    connected = Column(Boolean, default=False)
    last_read = Column(DateTime, nullable=True)
    read_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    uptime = Column(Float, default=0.0)
    
    def to_dict(self):
        """轉換為字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "connected": self.connected,
            "last_read": self.last_read.isoformat() if self.last_read else None,
            "read_count": self.read_count,
            "error_count": self.error_count,
            "uptime": self.uptime
        }