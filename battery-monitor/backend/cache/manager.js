import { createClient } from 'redis';
import winston from 'winston';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.Console({
      format: winston.format.simple()
    })
  ]
});

class CacheManager {
  constructor(config) {
    this.config = config;
    this.client = null;
    this.connected = false;
    this.ttl = {
      realtime: 10,
      cells: 10,
      history: 60,
      aggregated: 300
    };
  }

  async connect() {
    try {
      this.client = createClient({
        socket: {
          host: this.config.host || 'localhost',
          port: this.config.port || 6379
        },
        password: this.config.password || undefined
      });

      this.client.on('error', (err) => {
        logger.error('Redis client error:', err);
        this.connected = false;
      });

      this.client.on('connect', () => {
        logger.info('Redis client connected');
        this.connected = true;
      });

      await this.client.connect();
      return true;
    } catch (error) {
      logger.error('Failed to connect to Redis:', error);
      this.connected = false;
      return false;
    }
  }

  async setLatestData(key, data, ttl = null) {
    if (!this.connected) {
      logger.warn('Cache not connected, skipping set operation');
      return false;
    }

    try {
      const fullKey = `battery:latest:${key}`;
      const value = JSON.stringify(data);
      const expiry = ttl || this.ttl[key] || 60;

      await this.client.setEx(fullKey, expiry, value);
      return true;
    } catch (error) {
      logger.error(`Failed to cache ${key}:`, error);
      return false;
    }
  }

  async getLatestData(key) {
    if (!this.connected) {
      return null;
    }

    try {
      const fullKey = `battery:latest:${key}`;
      const value = await this.client.get(fullKey);
      
      if (value) {
        return JSON.parse(value);
      }
      
      return null;
    } catch (error) {
      logger.error(`Failed to get cached ${key}:`, error);
      return null;
    }
  }

  async cacheHistoryData(duration, data) {
    if (!this.connected) {
      return false;
    }

    try {
      const key = `battery:history:${duration}`;
      const value = JSON.stringify(data);
      const ttl = this.ttl.history;

      await this.client.setEx(key, ttl, value);
      return true;
    } catch (error) {
      logger.error(`Failed to cache history ${duration}:`, error);
      return false;
    }
  }

  async getCachedHistory(duration) {
    if (!this.connected) {
      return null;
    }

    try {
      const key = `battery:history:${duration}`;
      const value = await this.client.get(key);
      
      if (value) {
        return JSON.parse(value);
      }
      
      return null;
    } catch (error) {
      logger.error(`Failed to get cached history ${duration}:`, error);
      return null;
    }
  }

  async pushToQueue(queueName, data) {
    if (!this.connected) {
      return false;
    }

    try {
      const key = `battery:queue:${queueName}`;
      const value = JSON.stringify({
        timestamp: new Date().toISOString(),
        data: data
      });

      await this.client.lPush(key, value);
      
      await this.client.lTrim(key, 0, 999);
      
      return true;
    } catch (error) {
      logger.error(`Failed to push to queue ${queueName}:`, error);
      return false;
    }
  }

  async popFromQueue(queueName) {
    if (!this.connected) {
      return null;
    }

    try {
      const key = `battery:queue:${queueName}`;
      const value = await this.client.rPop(key);
      
      if (value) {
        return JSON.parse(value);
      }
      
      return null;
    } catch (error) {
      logger.error(`Failed to pop from queue ${queueName}:`, error);
      return null;
    }
  }

  async getQueueLength(queueName) {
    if (!this.connected) {
      return 0;
    }

    try {
      const key = `battery:queue:${queueName}`;
      return await this.client.lLen(key);
    } catch (error) {
      logger.error(`Failed to get queue length ${queueName}:`, error);
      return 0;
    }
  }

  async flush() {
    if (!this.connected) {
      return false;
    }

    try {
      await this.client.flushDb();
      logger.info('Cache flushed');
      return true;
    } catch (error) {
      logger.error('Failed to flush cache:', error);
      return false;
    }
  }

  async disconnect() {
    if (this.client) {
      await this.client.quit();
      this.connected = false;
      logger.info('Redis client disconnected');
    }
  }
}

export default CacheManager;