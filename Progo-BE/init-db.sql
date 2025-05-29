-- Initialize database with extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better performance
-- These will be created automatically by Alembic migrations
-- but we can add them here for reference

-- Indexes for sensor_readings table
-- CREATE INDEX IF NOT EXISTS idx_sensor_readings_device_id ON sensor_readings(device_id);
-- CREATE INDEX IF NOT EXISTS idx_sensor_readings_timestamp ON sensor_readings(timestamp);
-- CREATE INDEX IF NOT EXISTS idx_sensor_readings_session_id ON sensor_readings(session_id);

-- Indexes for exercise_sessions table  
-- CREATE INDEX IF NOT EXISTS idx_exercise_sessions_device_id ON exercise_sessions(device_id);
-- CREATE INDEX IF NOT EXISTS idx_exercise_sessions_start_time ON exercise_sessions(start_time);

-- Create a view for exercise session summaries
-- CREATE OR REPLACE VIEW exercise_session_summary AS
-- SELECT 
--     es.id,
--     es.device_id,
--     es.start_time,
--     es.end_time,
--     es.exercise_type,
--     es.is_labeled,
--     COUNT(sr.id) as reading_count,
--     COUNT(el.id) as label_count
-- FROM exercise_sessions es
-- LEFT JOIN sensor_readings sr ON es.id = sr.session_id
-- LEFT JOIN exercise_labels el ON es.id = el.session_id
-- GROUP BY es.id;
