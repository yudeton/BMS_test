export const schema = `
CREATE TABLE IF NOT EXISTS battery_realtime (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  total_voltage REAL,
  current REAL,
  power REAL,
  soc REAL,
  temperature REAL,
  status TEXT
);

CREATE TABLE IF NOT EXISTS battery_cells (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  cell_number INTEGER NOT NULL,
  voltage REAL NOT NULL,
  INDEX idx_cell_timestamp (timestamp, cell_number)
);

CREATE TABLE IF NOT EXISTS battery_aggregated (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp DATETIME NOT NULL,
  interval_type TEXT NOT NULL,
  total_voltage_avg REAL,
  total_voltage_max REAL,
  total_voltage_min REAL,
  current_avg REAL,
  current_max REAL,
  current_min REAL,
  power_avg REAL,
  power_max REAL,
  power_min REAL,
  soc_avg REAL,
  temperature_avg REAL,
  UNIQUE(timestamp, interval_type)
);

CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  alert_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  message TEXT NOT NULL,
  value REAL,
  acknowledged BOOLEAN DEFAULT FALSE,
  acknowledged_at DATETIME,
  INDEX idx_alert_timestamp (timestamp),
  INDEX idx_alert_severity (severity)
);

CREATE INDEX IF NOT EXISTS idx_realtime_timestamp ON battery_realtime(timestamp);
CREATE INDEX IF NOT EXISTS idx_cells_timestamp ON battery_cells(timestamp);
CREATE INDEX IF NOT EXISTS idx_aggregated_timestamp ON battery_aggregated(timestamp, interval_type);
`;