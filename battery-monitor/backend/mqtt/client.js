import mqtt from 'mqtt';
import EventEmitter from 'events';
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

class MqttClient extends EventEmitter {
  constructor(config) {
    super();
    this.config = config;
    this.client = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectInterval = 5000;
  }

  connect() {
    const options = {
      clientId: this.config.clientId || 'battery-monitor',
      username: this.config.username,
      password: this.config.password,
      clean: true,
      reconnectPeriod: this.reconnectInterval,
      connectTimeout: 30000
    };

    this.client = mqtt.connect(this.config.brokerUrl, options);

    this.client.on('connect', () => {
      logger.info('Connected to MQTT broker');
      this.reconnectAttempts = 0;
      this.subscribeToTopics();
    });

    this.client.on('message', (topic, message) => {
      try {
        const data = JSON.parse(message.toString());
        this.handleMessage(topic, data);
      } catch (error) {
        logger.error('Failed to parse MQTT message:', error);
      }
    });

    this.client.on('error', (error) => {
      logger.error('MQTT connection error:', error);
      this.emit('error', error);
    });

    this.client.on('offline', () => {
      logger.warn('MQTT client offline');
      this.emit('offline');
    });

    this.client.on('reconnect', () => {
      this.reconnectAttempts++;
      logger.info(`Reconnecting to MQTT broker (attempt ${this.reconnectAttempts})`);
      
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        logger.error('Max reconnection attempts reached');
        this.client.end();
        this.emit('max_reconnect_exceeded');
      }
    });
  }

  subscribeToTopics() {
    const topics = [
      `${this.config.topicPrefix}realtime`,
      `${this.config.topicPrefix}cells`,
      `${this.config.topicPrefix}alerts`,
      `${this.config.topicPrefix}status`
    ];

    topics.forEach(topic => {
      this.client.subscribe(topic, (err) => {
        if (err) {
          logger.error(`Failed to subscribe to ${topic}:`, err);
        } else {
          logger.info(`Subscribed to ${topic}`);
        }
      });
    });
  }

  handleMessage(topic, data) {
    const topicSuffix = topic.replace(this.config.topicPrefix, '');
    
    switch (topicSuffix) {
      case 'realtime':
        this.emit('realtime_data', this.parseRealtimeData(data));
        break;
      
      case 'cells':
        this.emit('cells_data', data);
        break;
      
      case 'alerts':
        this.emit('alert', this.parseAlert(data));
        break;
      
      case 'status':
        this.emit('status', data);
        break;
      
      default:
        logger.warn(`Unknown topic: ${topic}`);
    }
  }

  parseRealtimeData(data) {
    return {
      total_voltage: data.voltage || data.total_voltage || 0,
      current: data.current || 0,
      power: data.power || (data.voltage * data.current) || 0,
      soc: data.soc || data.state_of_charge || 0,
      temperature: data.temperature || data.temp || null,
      status: data.status || 'normal',
      cells: data.cells || []
    };
  }

  parseAlert(data) {
    const severityMap = {
      'critical': 'critical',
      'error': 'error',
      'warning': 'warning',
      'info': 'info'
    };

    return {
      alert_type: data.type || 'unknown',
      severity: severityMap[data.severity] || 'warning',
      message: data.message || 'Unknown alert',
      value: data.value || null
    };
  }

  publish(topic, data) {
    if (!this.client || !this.client.connected) {
      logger.error('Cannot publish - MQTT client not connected');
      return false;
    }

    const fullTopic = `${this.config.topicPrefix}${topic}`;
    const message = JSON.stringify(data);

    this.client.publish(fullTopic, message, (err) => {
      if (err) {
        logger.error(`Failed to publish to ${fullTopic}:`, err);
      }
    });

    return true;
  }

  disconnect() {
    if (this.client) {
      this.client.end();
      logger.info('MQTT client disconnected');
    }
  }
}

export default MqttClient;