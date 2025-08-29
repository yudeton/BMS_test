import redis.asyncio as aioredis
import json
import logging
from typing import Optional, Any, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CacheService:
    """Redis 緩存服務"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.connected = False
    
    async def connect(self):
        """連接到 Redis"""
        try:
            self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
            # 測試連接
            await self.redis.ping()
            self.connected = True
            logger.info("Redis 緩存服務已連接")
        except Exception as e:
            logger.error(f"Redis 連接失敗: {e}")
            self.connected = False
            raise
    
    async def disconnect(self):
        """斷開 Redis 連接"""
        if self.redis:
            await self.redis.close()
            self.connected = False
            logger.info("Redis 緩存服務已斷開")
    
    def is_connected(self) -> bool:
        """檢查連接狀態"""
        return self.connected
    
    async def set_data(self, key: str, value: Any, expire: Optional[int] = None):
        """設置緩存數據"""
        if not self.connected:
            logger.warning("Redis 未連接，無法設置數據")
            return False
        
        try:
            json_value = json.dumps(value, default=str)
            await self.redis.set(key, json_value, ex=expire)
            return True
        except Exception as e:
            logger.error(f"設置緩存數據失敗: {e}")
            return False
    
    async def get_data(self, key: str) -> Optional[Any]:
        """獲取緩存數據"""
        if not self.connected:
            logger.warning("Redis 未連接，無法獲取數據")
            return None
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"獲取緩存數據失敗: {e}")
            return None
    
    async def delete_data(self, key: str) -> bool:
        """刪除緩存數據"""
        if not self.connected:
            return False
        
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"刪除緩存數據失敗: {e}")
            return False
    
    async def set_latest_data(self, data_type: str, data: Dict[str, Any]):
        """設置最新數據"""
        key = f"latest:{data_type}"
        await self.set_data(key, data, expire=300)  # 5分鐘過期
    
    async def get_latest_data(self, data_type: str) -> Optional[Dict[str, Any]]:
        """獲取最新數據"""
        key = f"latest:{data_type}"
        return await self.get_data(key)
    
    async def set_history_data(self, data: Dict[str, Any]):
        """設置歷史數據 (使用時間戳作為 key)"""
        timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        key = f"history:{timestamp}"
        await self.set_data(key, data, expire=86400)  # 24小時過期
    
    async def get_history_data(self, start_time: datetime, end_time: datetime) -> list:
        """獲取時間範圍內的歷史數據"""
        if not self.connected:
            return []
        
        try:
            # 簡化實現：獲取所有歷史 key 並篩選
            pattern = "history:*"
            keys = await self.redis.keys(pattern)
            
            results = []
            for key in keys:
                data = await self.get_data(key)
                if data and "timestamp" in data:
                    data_time = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
                    if start_time <= data_time <= end_time:
                        results.append(data)
            
            # 按時間戳排序
            results.sort(key=lambda x: x.get("timestamp", ""))
            return results
        except Exception as e:
            logger.error(f"獲取歷史數據失敗: {e}")
            return []
    
    async def clear_expired_data(self):
        """清理過期數據（可選的維護任務）"""
        try:
            # Redis 會自動處理過期數據，這裡可以添加額外的清理邏輯
            logger.info("執行緩存數據清理")
        except Exception as e:
            logger.error(f"清理緩存數據失敗: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """獲取緩存統計信息"""
        if not self.connected:
            return {"connected": False}
        
        try:
            info = await self.redis.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
        except Exception as e:
            logger.error(f"獲取緩存統計失敗: {e}")
            return {"connected": False, "error": str(e)}