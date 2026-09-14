CREATE TABLE sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    reading_value TEXT NOT NULL,
    recorded_at TEXT NOT NULL
)
