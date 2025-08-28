import express from 'express';

const router = express.Router();

router.get('/realtime', async (req, res) => {
  try {
    const cached = await req.cache.getLatestData('realtime');
    if (cached) {
      return res.json(cached);
    }
    
    const data = req.db.getLatestData();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.get('/history/:duration', (req, res) => {
  try {
    const durationMap = {
      '1h': '-1 hour',
      '24h': '-24 hours',
      '7d': '-7 days',
      '30d': '-30 days'
    };
    
    const duration = durationMap[req.params.duration] || '-1 hour';
    const data = req.db.getHistoryData(duration);
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.get('/cells', async (req, res) => {
  try {
    const cached = await req.cache.getLatestData('cells');
    if (cached) {
      return res.json(cached);
    }
    
    const data = req.db.statements.getCellsLatest.all();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.get('/alerts', (req, res) => {
  try {
    const alerts = req.db.statements.getActiveAlerts.all();
    res.json(alerts);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.post('/alerts/:id/acknowledge', (req, res) => {
  try {
    const stmt = req.db.db.prepare(`
      UPDATE alerts 
      SET acknowledged = 1, acknowledged_at = CURRENT_TIMESTAMP 
      WHERE id = ?
    `);
    
    const result = stmt.run(req.params.id);
    
    if (result.changes > 0) {
      res.json({ success: true });
    } else {
      res.status(404).json({ error: 'Alert not found' });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.get('/aggregated/:interval', (req, res) => {
  try {
    const validIntervals = ['3min', '1hour', '1day'];
    const interval = req.params.interval;
    
    if (!validIntervals.includes(interval)) {
      return res.status(400).json({ error: 'Invalid interval' });
    }
    
    const durationMap = {
      '3min': '-1 day',
      '1hour': '-7 days',
      '1day': '-30 days'
    };
    
    const stmt = req.db.db.prepare(`
      SELECT * FROM battery_aggregated
      WHERE interval_type = ?
      AND timestamp >= datetime('now', ?)
      ORDER BY timestamp DESC
    `);
    
    const data = stmt.all(interval, durationMap[interval]);
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.get('/stats', async (req, res) => {
  try {
    const stats = {
      totalRecords: req.db.db.prepare('SELECT COUNT(*) as count FROM battery_realtime').get().count,
      activeAlerts: req.db.db.prepare('SELECT COUNT(*) as count FROM alerts WHERE acknowledged = 0').get().count,
      connectedClients: req.wsServer.getConnectedClients().length,
      uptime: process.uptime()
    };
    
    res.json(stats);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

export default router;