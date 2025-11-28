-- Create data warehouse database
SELECT 'CREATE DATABASE earthquake_dw'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'earthquake_dw')\gexec

-- Connect to earthquake_dw
\c earthquake_dw

-- Create user for data warehouse
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'dwuser') THEN
      CREATE USER dwuser WITH PASSWORD 'dwpassword';
   END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE earthquake_dw TO dwuser;
GRANT ALL PRIVILEGES ON SCHEMA public TO dwuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO dwuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO dwuser;

-- Create raw data table (ELT: Load raw data exactly as it comes)
CREATE TABLE IF NOT EXISTS raw_earthquakes (
    id SERIAL PRIMARY KEY,
    fecha_utc TEXT,
    hora_utc TEXT,
    magnitud TEXT,
    latitud TEXT,
    longitud TEXT,
    profundidad TEXT,
    referencia_localizacion TEXT,
    fecha_local TEXT,
    hora_local TEXT,
    estatus TEXT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    batch_id TEXT
);

-- Create analytics table (ELT: Transformed data for analysis)
CREATE TABLE IF NOT EXISTS analytics_earthquakes (
    id SERIAL PRIMARY KEY,
    earthquake_date DATE,
    earthquake_datetime TIMESTAMP,
    magnitude NUMERIC(3,1),
    latitude NUMERIC(8,5),
    longitude NUMERIC(8,5),
    depth_km NUMERIC(6,2),
    location_reference TEXT,
    status TEXT,
    year INTEGER,
    month INTEGER,
    day_of_week TEXT,
    hour_of_day INTEGER,
    magnitude_category TEXT,
    depth_category TEXT,
    region TEXT,
    is_significant BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    batch_id TEXT
);

-- Create aggregated statistics table
CREATE TABLE IF NOT EXISTS earthquake_statistics (
    id SERIAL PRIMARY KEY,
    calculation_date DATE DEFAULT CURRENT_DATE,
    total_earthquakes INTEGER,
    avg_magnitude NUMERIC(4,2),
    max_magnitude NUMERIC(3,1),
    min_magnitude NUMERIC(3,1),
    avg_depth NUMERIC(6,2),
    significant_count INTEGER,
    by_magnitude_category JSONB,
    by_region JSONB,
    by_month JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_raw_batch_id ON raw_earthquakes(batch_id);
CREATE INDEX IF NOT EXISTS idx_raw_loaded_at ON raw_earthquakes(loaded_at);
CREATE INDEX IF NOT EXISTS idx_analytics_date ON analytics_earthquakes(earthquake_date);
CREATE INDEX IF NOT EXISTS idx_analytics_magnitude ON analytics_earthquakes(magnitude);
CREATE INDEX IF NOT EXISTS idx_analytics_region ON analytics_earthquakes(region);
CREATE INDEX IF NOT EXISTS idx_analytics_batch_id ON analytics_earthquakes(batch_id);

-- Grant permissions on tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dwuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dwuser;

COMMENT ON TABLE raw_earthquakes IS 'Raw earthquake data loaded without transformation (ELT Extract-Load phase)';
COMMENT ON TABLE analytics_earthquakes IS 'Transformed earthquake data ready for analysis (ELT Transform phase)';
COMMENT ON TABLE earthquake_statistics IS 'Aggregated statistics calculated from analytics layer';
