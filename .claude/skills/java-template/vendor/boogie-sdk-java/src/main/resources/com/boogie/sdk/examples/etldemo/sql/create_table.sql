CREATE TABLE sensor_readings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    contact_phone VARCHAR(50) NOT NULL,
    reading_value VARCHAR(50) NOT NULL,
    recorded_at VARCHAR(50) NOT NULL
)
