import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import cron from 'node-cron';
import path from 'path';
import { fileURLToPath } from 'url';
import winston from 'winston';

import BatteryDatabase from './db/database.js';
import MqttClient from './mqtt/client.js';
import WSServer from './websocket/server.js';
import apiRouter from './api/router.js';
import CacheManager from './cache/manager.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.simple()
    }),
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});

class BatteryMonitorServer {
  constructor() {
    this.app = express();
    this.db = new BatteryDatabase(process.env.DB_PATH);
    this.cache = new CacheManager({
      host: process.env.REDIS_HOST,
      port: process.env.REDIS_PORT,
      password: process.env.REDIS_PASSWORD
    });
    
    this.mqttClient = new MqttClient({
      brokerUrl: process.env.MQTT_BROKER_URL,
      clientId: process.env.MQTT_CLIENT_ID,
      username: process.env.MQTT_USERNAME,
      password: process.env.MQTT_PASSWORD,
      topicPrefix: process.env.MQTT_TOPIC_PREFIX
    });
    
    this.wsServer = new WSServer(parseInt(process.env.WS_PORT));
    
    this.setupMiddleware();
    this.setupRoutes();
    this.setupEventHandlers();
    this.setupCronJobs();
  }

  setupMiddleware() {
    this.app.use(cors());
    this.app.use(express.json());
    this.app.use(express.static(path.join(__dirname, '../frontend/build')));
    
    this.app.use((req, res, next) => {
      req.db = this.db;
      req.cache = this.cache;
      req.wsServer = this.wsServer;
      next();
    });
  }

  setupRoutes() {
    this.app.use('/api', apiRouter);
    
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        connections: {
          mqtt: this.mqttClient.client?.connected || false,
          websocket: this.wsServer.getConnectedClients().length
        }
      });
    });
    
    this.app.get('*', (req, res) => {
      res.sendFile(path.join(__dirname, '../frontend/build/index.html'));
    });
  }

  setupEventHandlers() {
    this.mqttClient.on('realtime_data', async (data) => {
      try {
        const rowId = this.db.saveRealtimeData(data);
        
        await this.cache.setLatestData('realtime', data);
        
        this.wsServer.broadcast(data, 'realtime');
        
        this.checkAlerts(data);
        
        logger.info('Realtime data saved:', { rowId, voltage: data.total_voltage, soc: data.soc });
      } catch (error) {
        logger.error('Failed to process realtime data:', error);
      }
    });
    
    this.mqttClient.on('cells_data', async (data) => {
      try {
        await this.cache.setLatestData('cells', data);
        this.wsServer.broadcast(data, 'cells');
      } catch (error) {
        logger.error('Failed to process cells data:', error);
      }
    });
    
    this.mqttClient.on('alert', (alert) => {
      try {
        this.db.saveAlert(alert);
        this.wsServer.broadcast(alert, 'alerts');
        logger.warn('Alert received:', alert);
      } catch (error) {
        logger.error('Failed to process alert:', error);
      }
    });
    
    this.mqttClient.on('error', (error) => {
      logger.error('MQTT error:', error);
    });
    
    this.mqttClient.on('max_reconnect_exceeded', () => {
      logger.error('MQTT max reconnection attempts exceeded');
    });
  }

  checkAlerts(data) {
    const alerts = [];
    
    if (data.total_voltage < 40) {
      alerts.push({
        alert_type: 'low_voltage',
        severity: 'critical',
        message: `Battery voltage critically low: ${data.total_voltage}V`,
        value: data.total_voltage
      });
    } else if (data.total_voltage < 45) {
      alerts.push({
        alert_type: 'low_voltage',
        severity: 'warning',
        message: `Battery voltage low: ${data.total_voltage}V`,
        value: data.total_voltage
      });
    }
    
    if (data.total_voltage > 58) {
      alerts.push({
        alert_type: 'high_voltage',
        severity: 'warning',
        message: `Battery voltage high: ${data.total_voltage}V`,
        value: data.total_voltage
      });
    }
    
    if (Math.abs(data.current) > 100) {
      alerts.push({
        alert_type: 'high_current',
        severity: 'warning',
        message: `High current detected: ${data.current}A`,
        value: data.current
      });
    }
    
    if (data.temperature && data.temperature > 45) {
      alerts.push({
        alert_type: 'high_temperature',
        severity: data.temperature > 55 ? 'critical' : 'warning',
        message: `High temperature: ${data.temperature}°C`,
        value: data.temperature
      });
    }
    
    if (data.soc < 20) {
      alerts.push({
        alert_type: 'low_soc',
        severity: data.soc < 10 ? 'critical' : 'warning',
        message: `Low battery SOC: ${data.soc}%`,
        value: data.soc
      });
    }
    
    alerts.forEach(alert => {
      this.db.saveAlert(alert);
      this.wsServer.broadcast(alert, 'alerts');
    });
  }

  setupCronJobs() {
    cron.schedule('*/3 * * * *', () => {
      logger.info('Running 3-minute data aggregation');
      this.db.aggregateData(3);
    });
    
    cron.schedule('0 * * * *', () => {
      logger.info('Running hourly data aggregation');
      this.db.aggregateData(60);
    });
    
    cron.schedule('0 0 * * *', () => {
      logger.info('Running daily cleanup');
      const retentionDays = parseInt(process.env.DATA_RETENTION_DAYS) || 30;
      
    });
  }

  async start() {
    try {
      await this.cache.connect();
      logger.info('Cache connected');
      
      this.mqttClient.connect();
      
      this.wsServer.start();
      
      const port = process.env.PORT || 3001;
      this.app.listen(port, () => {
        logger.info(`HTTP server running on port ${port}`);
        logger.info(`WebSocket server running on port ${process.env.WS_PORT}`);
      });
    } catch (error) {
      logger.error('Failed to start server:', error);
      process.exit(1);
    }
  }

  async stop() {
    logger.info('Shutting down server...');
    
    this.mqttClient.disconnect();
    this.wsServer.stop();
    await this.cache.disconnect();
    this.db.close();
    
    logger.info('Server shut down');
  }
}

const server = new BatteryMonitorServer();

server.start();

process.on('SIGINT', async () => {
  await server.stop();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await server.stop();
  process.exit(0);
});