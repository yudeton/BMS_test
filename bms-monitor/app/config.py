from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """應用設定"""
    
    # FastAPI 設定
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    ws_port: int = 8001
    
    # 資料庫設定
    database_url: str = "sqlite+aiosqlite:///./battery.db"
    db_path: str = "./battery.db"
    
    # Redis 設定
    redis_url: str = "redis://localhost:6379"
    redis_host: str = "localhost"
    redis_port: int = 6379
    
    # MQTT 設定
    mqtt_broker_url: str = "mqtt://localhost:1883"
    mqtt_client_id: str = "fastapi-battery-monitor"
    mqtt_topic_prefix: str = "battery"
    
    # BMS 設定
    bms_mac_address: str = "41:18:12:01:37:71"
    bms_read_interval: int = 30
    
    # 日誌設定
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()