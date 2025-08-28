import Database from 'better-sqlite3';
import { schema } from './schema.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class BatteryDatabase {
  constructor(dbPath) {
    this.db = new Database(dbPath || path.join(__dirname, '../data/battery.db'));
    this.initialize();
  }

  initialize() {
    this.db.exec(schema);
    this.prepareStatements();
  }

  prepareStatements() {
    this.statements = {
      insertRealtime: this.db.prepare(`
        INSERT INTO battery_realtime (total_voltage, current, power, soc, temperature, status)
        VALUES (@total_voltage, @current, @power, @soc, @temperature, @status)
      `),
      
      insertCell: this.db.prepare(`
        INSERT INTO battery_cells (cell_number, voltage)
        VALUES (@cell_number, @voltage)
      `),
      
      insertAlert: this.db.prepare(`
        INSERT INTO alerts (alert_type, severity, message, value)
        VALUES (@alert_type, @severity, @message, @value)
      `),
      
      getLatestRealtime: this.db.prepare(`
        SELECT * FROM battery_realtime
        ORDER BY timestamp DESC
        LIMIT 1
      `),
      
      getRealtimeHistory: this.db.prepare(`
        SELECT * FROM battery_realtime
        WHERE timestamp >= datetime('now', ?)
        ORDER BY timestamp DESC
      `),
      
      getCellsLatest: this.db.prepare(`
        SELECT cell_number, voltage
        FROM battery_cells
        WHERE timestamp = (SELECT MAX(timestamp) FROM battery_cells)
        ORDER BY cell_number
      `),
      
      getActiveAlerts: this.db.prepare(`
        SELECT * FROM alerts
        WHERE acknowledged = 0
        ORDER BY timestamp DESC
      `)
    };
  }

  saveRealtimeData(data) {
    const transaction = this.db.transaction((data) => {
      const info = this.statements.insertRealtime.run(data);
      
      if (data.cells && Array.isArray(data.cells)) {
        for (let i = 0; i < data.cells.length; i++) {
          this.statements.insertCell.run({
            cell_number: i + 1,
            voltage: data.cells[i]
          });
        }
      }
      
      return info.lastInsertRowid;
    });
    
    return transaction(data);
  }

  saveAlert(alert) {
    return this.statements.insertAlert.run(alert);
  }

  getLatestData() {
    return {
      realtime: this.statements.getLatestRealtime.get(),
      cells: this.statements.getCellsLatest.all(),
      alerts: this.statements.getActiveAlerts.all()
    };
  }

  getHistoryData(duration = '-1 hour') {
    return this.statements.getRealtimeHistory.all(duration);
  }

  aggregateData(intervalMinutes = 3) {
    const query = `
      INSERT INTO battery_aggregated (timestamp, interval_type, 
        total_voltage_avg, total_voltage_max, total_voltage_min,
        current_avg, current_max, current_min,
        power_avg, power_max, power_min,
        soc_avg, temperature_avg)
      SELECT 
        datetime((strftime('%s', timestamp) / (${intervalMinutes} * 60)) * (${intervalMinutes} * 60), 'unixepoch') as interval_time,
        '${intervalMinutes}min' as interval_type,
        AVG(total_voltage), MAX(total_voltage), MIN(total_voltage),
        AVG(current), MAX(current), MIN(current),
        AVG(power), MAX(power), MIN(power),
        AVG(soc), AVG(temperature)
      FROM battery_realtime
      WHERE timestamp >= datetime('now', '-${intervalMinutes} minutes')
      GROUP BY interval_time
      ON CONFLICT(timestamp, interval_type) DO UPDATE SET
        total_voltage_avg = excluded.total_voltage_avg,
        total_voltage_max = excluded.total_voltage_max,
        total_voltage_min = excluded.total_voltage_min,
        current_avg = excluded.current_avg,
        current_max = excluded.current_max,
        current_min = excluded.current_min,
        power_avg = excluded.power_avg,
        power_max = excluded.power_max,
        power_min = excluded.power_min,
        soc_avg = excluded.soc_avg,
        temperature_avg = excluded.temperature_avg
    `;
    
    return this.db.prepare(query).run();
  }

  close() {
    this.db.close();
  }
}

export default BatteryDatabase;