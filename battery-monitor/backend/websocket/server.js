import { WebSocketServer } from 'ws';
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

class WSServer extends EventEmitter {
  constructor(port = 3002) {
    super();
    this.port = port;
    this.wss = null;
    this.clients = new Map();
    this.messageQueue = new Map();
    this.heartbeatInterval = 30000;
  }

  start() {
    this.wss = new WebSocketServer({ port: this.port });
    
    this.wss.on('connection', (ws, req) => {
      const clientId = this.generateClientId();
      const clientInfo = {
        id: clientId,
        ws: ws,
        ip: req.socket.remoteAddress,
        connectedAt: new Date(),
        isAlive: true,
        subscriptions: new Set(['realtime'])
      };
      
      this.clients.set(clientId, clientInfo);
      logger.info(`Client ${clientId} connected from ${clientInfo.ip}`);
      
      ws.on('message', (message) => {
        this.handleClientMessage(clientId, message);
      });
      
      ws.on('pong', () => {
        clientInfo.isAlive = true;
      });
      
      ws.on('close', () => {
        logger.info(`Client ${clientId} disconnected`);
        this.clients.delete(clientId);
        this.messageQueue.delete(clientId);
      });
      
      ws.on('error', (error) => {
        logger.error(`WebSocket error for client ${clientId}:`, error);
      });
      
      this.sendToClient(clientId, {
        type: 'connection',
        clientId: clientId,
        message: 'Connected to battery monitor'
      });
      
      if (this.messageQueue.has(clientId)) {
        const queue = this.messageQueue.get(clientId);
        queue.forEach(msg => this.sendToClient(clientId, msg));
        this.messageQueue.delete(clientId);
      }
    });
    
    this.startHeartbeat();
    logger.info(`WebSocket server started on port ${this.port}`);
  }

  handleClientMessage(clientId, message) {
    try {
      const data = JSON.parse(message);
      const client = this.clients.get(clientId);
      
      if (!client) return;
      
      switch (data.type) {
        case 'subscribe':
          if (data.topics && Array.isArray(data.topics)) {
            data.topics.forEach(topic => client.subscriptions.add(topic));
            this.sendToClient(clientId, {
              type: 'subscribed',
              topics: data.topics
            });
          }
          break;
        
        case 'unsubscribe':
          if (data.topics && Array.isArray(data.topics)) {
            data.topics.forEach(topic => client.subscriptions.delete(topic));
            this.sendToClient(clientId, {
              type: 'unsubscribed',
              topics: data.topics
            });
          }
          break;
        
        case 'ping':
          this.sendToClient(clientId, { type: 'pong' });
          break;
        
        default:
          this.emit('client_message', { clientId, data });
      }
    } catch (error) {
      logger.error(`Failed to parse message from client ${clientId}:`, error);
    }
  }

  broadcast(data, topic = 'realtime') {
    const message = JSON.stringify({
      type: 'data',
      topic: topic,
      timestamp: new Date().toISOString(),
      data: data
    });
    
    this.clients.forEach((client, clientId) => {
      if (client.subscriptions.has(topic) && client.ws.readyState === 1) {
        try {
          client.ws.send(message);
        } catch (error) {
          logger.error(`Failed to send to client ${clientId}:`, error);
          this.queueMessage(clientId, data);
        }
      }
    });
  }

  sendToClient(clientId, data) {
    const client = this.clients.get(clientId);
    
    if (!client || client.ws.readyState !== 1) {
      this.queueMessage(clientId, data);
      return false;
    }
    
    try {
      client.ws.send(JSON.stringify(data));
      return true;
    } catch (error) {
      logger.error(`Failed to send to client ${clientId}:`, error);
      this.queueMessage(clientId, data);
      return false;
    }
  }

  queueMessage(clientId, data) {
    if (!this.messageQueue.has(clientId)) {
      this.messageQueue.set(clientId, []);
    }
    
    const queue = this.messageQueue.get(clientId);
    queue.push(data);
    
    if (queue.length > 100) {
      queue.shift();
    }
  }

  startHeartbeat() {
    setInterval(() => {
      this.clients.forEach((client, clientId) => {
        if (!client.isAlive) {
          logger.warn(`Client ${clientId} failed heartbeat check`);
          client.ws.terminate();
          this.clients.delete(clientId);
          return;
        }
        
        client.isAlive = false;
        client.ws.ping();
      });
    }, this.heartbeatInterval);
  }

  generateClientId() {
    return 'client_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  getConnectedClients() {
    return Array.from(this.clients.values()).map(client => ({
      id: client.id,
      ip: client.ip,
      connectedAt: client.connectedAt,
      subscriptions: Array.from(client.subscriptions)
    }));
  }

  stop() {
    if (this.wss) {
      this.clients.forEach(client => client.ws.close());
      this.wss.close(() => {
        logger.info('WebSocket server stopped');
      });
    }
  }
}

export default WSServer;