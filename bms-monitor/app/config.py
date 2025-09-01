from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional

class Settings(BaseSettings):
    # 同時讀取根目錄與 bms-monitor 目錄的 .env（後者優先覆蓋）
    # 單一真實來源：使用專案根目錄的 .env（../.env）
    # Read env from project root .env and ignore unrelated keys from docker/frontend
    model_config = SettingsConfigDict(
        env_file=("../.env",),
        extra="ignore",
    )
    """應用設定"""
    
    # FastAPI 設定
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    ws_port: int = 8001
    
    # 資料庫設定 (SQLite - 暫時使用，稍後可改為 PostgreSQL)
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
    # SOC 解析設定（可依不同韌體調整）
    soc_register: int = 0x002C
    soc_scale: float = 0.1
    soc_offset: float = 0.0

    # 允許以 0x 前綴字串指定寄存器（環境變數）
    @field_validator('soc_register', mode='before')
    @classmethod
    def _parse_soc_register(cls, v):
        if isinstance(v, str):
            s = v.strip()
            if s.lower().startswith('0x'):
                return int(s, 16)
        return v
    
    # 日誌設定
    log_level: str = "INFO"

settings = Settings()
