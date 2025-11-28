"""
Earthquake ELT Pipeline DAG
===========================
This DAG implements a full ELT (Extract-Load-Transform) process for earthquake data analysis.

Social/Environmental Impact:
- Helps analyze seismic patterns in Mexico for disaster preparedness
- Supports policy-making for building codes and emergency response
- Benefits: Civil protection agencies, urban planners, researchers, and citizens

ELT Justification:
- Dataset grows continuously as new earthquakes occur
- Raw data must be preserved for historical analysis and audit trails
- Transformations may evolve as new analytical needs emerge
- Enables data scientists to create new features without re-extraction
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.task_group import TaskGroup
import pandas as pd
import os
import logging
from typing import Dict, Any
import unicodedata

# Configuration
RAW_DATA_PATH = '/opt/airflow/data/raw'
ANALYTICS_DATA_PATH = '/opt/airflow/data/analytics'
CSV_FILE = f"{RAW_DATA_PATH}/Sismos.csv"
DW_CONN_ID = 'earthquake_dw'

# Default arguments with error handling
default_args = {
    'owner': 'data_engineering_team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=30),
}

def normalize_column_name(col_name: str) -> str:
    """
    Normalize column names to match database schema:
    - Remove accents
    - Convert to lowercase
    - Replace spaces with underscores
    - Remove special characters
    """
    # Remove accents
    col_name = ''.join(
        c for c in unicodedata.normalize('NFD', col_name)
        if unicodedata.category(c) != 'Mn'
    )
    # Convert to lowercase and replace spaces
    col_name = col_name.strip().lower().replace(' ', '_')
    # Remove any remaining special characters except underscore
    col_name = ''.join(c if c.isalnum() or c == '_' else '' for c in col_name)
    return col_name

def extract_earthquake_data(**context) -> Dict[str, Any]:
    """
    EXTRACT Phase: Load raw CSV data
    In production, this would call an API or download from a source.
    For this project, we simulate periodic data extraction.
    """
    try:
        logging.info("Starting data extraction...")
        
        # Check if CSV exists
        if not os.path.exists(CSV_FILE):
            raise FileNotFoundError(f"CSV file not found: {CSV_FILE}")
        
        # Read CSV - Force all columns to string to preserve raw data
        # This handles mixed types and aligns with ELT philosophy
        df = pd.read_csv(CSV_FILE, dtype=str, low_memory=False)
        logging.info(f"Extracted {len(df)} records from CSV")
        logging.info(f"Original columns: {list(df.columns)}")
        
        # Normalize column names immediately after reading
        df.columns = [normalize_column_name(col) for col in df.columns]
        logging.info(f"Normalized columns: {list(df.columns)}")
        
        # Generate batch ID for tracking
        batch_id = context['ts_nodash']
        
        # Save to raw data folder (partitioned by batch)
        os.makedirs(RAW_DATA_PATH, exist_ok=True)
        raw_file = f"{RAW_DATA_PATH}/earthquakes_raw_{batch_id}.parquet"
        
        # Save to parquet with explicit string handling
        df.to_parquet(raw_file, index=False, engine='pyarrow')
        
        logging.info(f"Raw data saved to {raw_file}")
        
        # Push metadata to XCom
        context['ti'].xcom_push(key='batch_id', value=batch_id)
        context['ti'].xcom_push(key='raw_file', value=raw_file)
        context['ti'].xcom_push(key='record_count', value=len(df))
        
        return {
            'status': 'success',
            'records': len(df),
            'batch_id': batch_id
        }
    
    except Exception as e:
        logging.error(f"Extract failed: {str(e)}")
        raise

def load_raw_data(**context) -> Dict[str, Any]:
    """
    LOAD Phase: Load raw data into database WITHOUT any transformation
    This is the key difference from ETL - we load data exactly as it comes
    """
    try:
        logging.info("Starting raw data load...")
        
        # Get batch info from previous task
        batch_id = context['ti'].xcom_pull(key='batch_id', task_ids='extract_data')
        raw_file = context['ti'].xcom_pull(key='raw_file', task_ids='extract_data')
        
        # Read raw parquet file
        df = pd.read_parquet(raw_file)
        
        logging.info(f"Loaded parquet with columns: {list(df.columns)}")
        
        # Map column names to match database schema exactly
        # The database has 'referencia_localizacion' without 'de'
        column_mapping = {
            'referencia_de_localizacion': 'referencia_localizacion'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        logging.info(f"Columns after mapping: {list(df.columns)}")
        
        # Add metadata columns
        df['batch_id'] = batch_id
        df['loaded_at'] = datetime.now()
        
        # Connect to data warehouse
        hook = PostgresHook(postgres_conn_id=DW_CONN_ID)
        engine = hook.get_sqlalchemy_engine()
        
        # Load raw data - NO TRANSFORMATION, EXACTLY AS IT COMES
        # All columns remain as TEXT to preserve original format
        df.to_sql(
            'raw_earthquakes',
            engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )
        
        logging.info(f"Loaded {len(df)} raw records to database (batch: {batch_id})")
        
        context['ti'].xcom_push(key='loaded_records', value=len(df))
        
        return {
            'status': 'success',
            'loaded_records': len(df),
            'batch_id': batch_id
        }
    
    except Exception as e:
        logging.error(f"Load failed: {str(e)}")
        raise

def validate_raw_data(**context) -> Dict[str, Any]:
    """
    Validation task: Check data quality of raw load
    """
    try:
        logging.info("Validating raw data load...")
        
        batch_id = context['ti'].xcom_pull(key='batch_id', task_ids='extract_data')
        hook = PostgresHook(postgres_conn_id=DW_CONN_ID)
        
        # Check record count
        query = f"""
        SELECT COUNT(*) as count 
        FROM raw_earthquakes 
        WHERE batch_id = '{batch_id}'
        """
        result = hook.get_first(query)
        loaded_count = result[0] if result else 0
        
        expected_count = context['ti'].xcom_pull(key='record_count', task_ids='extract_data')
        
        if loaded_count != expected_count:
            raise ValueError(f"Validation failed: Expected {expected_count}, got {loaded_count}")
        
        logging.info(f"Validation passed: {loaded_count} records confirmed")
        
        return {
            'status': 'success',
            'validated_records': loaded_count
        }
    
    except Exception as e:
        logging.error(f"Validation failed: {str(e)}")
        raise

def export_analytics_to_parquet(**context) -> Dict[str, Any]:
    """
    Export transformed data to Parquet for efficient dashboard access
    """
    try:
        logging.info("Exporting analytics data to Parquet...")
        
        batch_id = context['ti'].xcom_pull(key='batch_id', task_ids='extract_data')
        hook = PostgresHook(postgres_conn_id=DW_CONN_ID)
        
        # Read transformed data
        query = "SELECT * FROM analytics_earthquakes ORDER BY earthquake_datetime DESC"
        df = hook.get_pandas_df(query)
        
        # Create analytics directory
        os.makedirs(ANALYTICS_DATA_PATH, exist_ok=True)
        
        # Export to Parquet (compressed)
        output_file = f"{ANALYTICS_DATA_PATH}/earthquakes_analytics.parquet"
        df.to_parquet(output_file, index=False, compression='snappy')
        
        logging.info(f"Exported {len(df)} analytics records to {output_file}")
        
        return {
            'status': 'success',
            'exported_records': len(df),
            'file': output_file
        }
    
    except Exception as e:
        logging.error(f"Export failed: {str(e)}")
        raise

# SQL for transformations (runs INSIDE the database)
TRANSFORM_SQL = """
-- TRANSFORM Phase: Clean and transform raw data into analytics layer
-- This happens INSIDE the database, after the raw data is loaded

WITH parsed_data AS (
    SELECT 
        id,
        batch_id,
        -- Parse dates and times
        TO_DATE(fecha_utc, 'DD/MM/YYYY') as earthquake_date,
        TO_TIMESTAMP(fecha_utc || ' ' || hora_utc, 'DD/MM/YYYY HH24:MI:SS') as earthquake_datetime,
        
        -- Convert to proper numeric types (handle non-numeric values using regex validation)
        -- This handles 'no calculable', 'en revision', empty strings, and any other text
        CASE 
            WHEN TRIM(magnitud) ~ '^[0-9]+\.?[0-9]*$' THEN CAST(TRIM(magnitud) AS NUMERIC(3,1))
            ELSE NULL
        END as magnitude,
        CASE 
            WHEN TRIM(latitud) ~ '^-?[0-9]+\.?[0-9]*$' THEN CAST(TRIM(latitud) AS NUMERIC(8,5))
            ELSE NULL
        END as latitude,
        CASE 
            WHEN TRIM(longitud) ~ '^-?[0-9]+\.?[0-9]*$' THEN CAST(TRIM(longitud) AS NUMERIC(8,5))
            ELSE NULL
        END as longitude,
        CASE 
            WHEN TRIM(profundidad) ~ '^[0-9]+\.?[0-9]*$' THEN CAST(TRIM(profundidad) AS NUMERIC(6,2))
            ELSE NULL
        END as depth_km,
        
        -- Clean text fields
        TRIM(referencia_localizacion) as location_reference,
        LOWER(TRIM(estatus)) as status
    FROM raw_earthquakes
    WHERE batch_id = '{{ ti.xcom_pull(key="batch_id", task_ids="extract_data") }}'
)
INSERT INTO analytics_earthquakes (
    earthquake_date,
    earthquake_datetime,
    magnitude,
    latitude,
    longitude,
    depth_km,
    location_reference,
    status,
    year,
    month,
    day_of_week,
    hour_of_day,
    magnitude_category,
    depth_category,
    region,
    is_significant,
    batch_id
)
SELECT 
    earthquake_date,
    earthquake_datetime,
    magnitude,
    latitude,
    longitude,
    depth_km,
    location_reference,
    status,
    
    -- Feature engineering: Time-based features
    EXTRACT(YEAR FROM earthquake_date) as year,
    EXTRACT(MONTH FROM earthquake_date) as month,
    TO_CHAR(earthquake_date, 'Day') as day_of_week,
    EXTRACT(HOUR FROM earthquake_datetime) as hour_of_day,
    
    -- Feature engineering: Magnitude categorization
    CASE 
        WHEN magnitude < 3.0 THEN 'Minor'
        WHEN magnitude >= 3.0 AND magnitude < 4.0 THEN 'Light'
        WHEN magnitude >= 4.0 AND magnitude < 5.0 THEN 'Moderate'
        WHEN magnitude >= 5.0 AND magnitude < 6.0 THEN 'Strong'
        WHEN magnitude >= 6.0 AND magnitude < 7.0 THEN 'Major'
        WHEN magnitude >= 7.0 THEN 'Great'
        ELSE 'Unknown'
    END as magnitude_category,
    
    -- Feature engineering: Depth categorization
    CASE 
        WHEN depth_km < 70 THEN 'Shallow'
        WHEN depth_km >= 70 AND depth_km < 300 THEN 'Intermediate'
        WHEN depth_km >= 300 THEN 'Deep'
        ELSE 'Unknown'
    END as depth_category,
    
    -- Feature engineering: Region extraction
    CASE 
        WHEN location_reference ILIKE '%MICH%' THEN 'Michoacán'
        WHEN location_reference ILIKE '%OAXACA%' OR location_reference ILIKE '%OAX%' THEN 'Oaxaca'
        WHEN location_reference ILIKE '%GUERRERO%' OR location_reference ILIKE '%GRO%' THEN 'Guerrero'
        WHEN location_reference ILIKE '%CHIAPAS%' OR location_reference ILIKE '%CHIS%' THEN 'Chiapas'
        WHEN location_reference ILIKE '%CDMX%' OR location_reference ILIKE '%CIUDAD DE MEXICO%' THEN 'CDMX'
        WHEN location_reference ILIKE '%PUEBLA%' OR location_reference ILIKE '%PUE%' THEN 'Puebla'
        WHEN location_reference ILIKE '%VERACRUZ%' OR location_reference ILIKE '%VER%' THEN 'Veracruz'
        ELSE 'Other'
    END as region,
    
    -- Feature engineering: Significance flag
    (magnitude >= 5.0 OR depth_km < 50) as is_significant,
    
    batch_id
FROM parsed_data
WHERE magnitude IS NOT NULL 
  AND latitude IS NOT NULL 
  AND longitude IS NOT NULL;
"""

AGGREGATE_STATISTICS_SQL = """
-- Calculate aggregated statistics for dashboard KPIs
INSERT INTO earthquake_statistics (
    calculation_date,
    total_earthquakes,
    avg_magnitude,
    max_magnitude,
    min_magnitude,
    avg_depth,
    significant_count,
    by_magnitude_category,
    by_region,
    by_month
)
SELECT 
    CURRENT_DATE as calculation_date,
    COUNT(*) as total_earthquakes,
    ROUND(AVG(magnitude), 2) as avg_magnitude,
    MAX(magnitude) as max_magnitude,
    MIN(magnitude) as min_magnitude,
    ROUND(AVG(depth_km), 2) as avg_depth,
    SUM(CASE WHEN is_significant THEN 1 ELSE 0 END) as significant_count,
    
    -- Aggregate by magnitude category (stored as JSONB)
    (SELECT jsonb_object_agg(magnitude_category, count)
     FROM (
         SELECT magnitude_category, COUNT(*) as count
         FROM analytics_earthquakes
         GROUP BY magnitude_category
     ) mag_counts) as by_magnitude_category,
    
    -- Aggregate by region (stored as JSONB)
    (SELECT jsonb_object_agg(region, count)
     FROM (
         SELECT region, COUNT(*) as count
         FROM analytics_earthquakes
         GROUP BY region
         ORDER BY count DESC
         LIMIT 10
     ) region_counts) as by_region,
    
    -- Aggregate by month (stored as JSONB)
    (SELECT jsonb_object_agg(month, count)
     FROM (
         SELECT month, COUNT(*) as count
         FROM analytics_earthquakes
         GROUP BY month
         ORDER BY month
     ) month_counts) as by_month
    
FROM analytics_earthquakes;
"""

# Create DAG
with DAG(
    'earthquake_elt_pipeline',
    default_args=default_args,
    description='ELT pipeline for earthquake data analysis with social impact',
    schedule_interval='@daily',  # Run daily to simulate continuous data flow
    catchup=False,
    tags=['elt', 'earthquake', 'social-impact', 'disaster-preparedness'],
    doc_md=__doc__,
) as dag:
    
    # EXTRACT: Get raw data
    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=extract_earthquake_data,
        doc_md="""
        ### Extract Phase
        Extracts earthquake data from CSV source.
        In production, this would connect to real-time seismic APIs.
        """
    )
    
    # LOAD: Load raw data without transformation
    load_task = PythonOperator(
        task_id='load_raw_data',
        python_callable=load_raw_data,
        doc_md="""
        ### Load Phase (ELT Key Step)
        Loads raw data EXACTLY as it comes into the data warehouse.
        No transformations, no type conversions - just pure raw data.
        This preserves the original data for audit and reprocessing.
        """
    )
    
    # VALIDATE: Check data quality
    validate_task = PythonOperator(
        task_id='validate_raw_data',
        python_callable=validate_raw_data,
        doc_md="""
        ### Validation Phase
        Ensures data was loaded correctly.
        Part of error handling strategy.
        """
    )
    
    # TRANSFORM: Transform inside the database
    with TaskGroup('transform_data', tooltip='Transform raw data inside database') as transform_group:
        
        # Clean and transform raw data
        transform_task = PostgresOperator(
            task_id='transform_to_analytics',
            postgres_conn_id=DW_CONN_ID,
            sql=TRANSFORM_SQL,
            doc_md="""
            ### Transform Phase (ELT Key Step)
            Transforms raw data INSIDE the database using SQL.
            Creates cleaned, typed, and enriched analytics layer.
            Raw data remains untouched in raw_earthquakes table.
            """
        )
        
        # Calculate aggregated statistics
        aggregate_task = PostgresOperator(
            task_id='calculate_statistics',
            postgres_conn_id=DW_CONN_ID,
            sql=AGGREGATE_STATISTICS_SQL,
            doc_md="""
            ### Aggregation Phase
            Calculates KPIs and aggregated metrics for dashboard.
            Runs entirely in the database for performance.
            """
        )
        
        transform_task >> aggregate_task
    
    # EXPORT: Export to Parquet for dashboard
    export_task = PythonOperator(
        task_id='export_to_parquet',
        python_callable=export_analytics_to_parquet,
        doc_md="""
        ### Export Phase
        Exports transformed data to Parquet format.
        Enables efficient access for dashboard and analysis.
        """
    )
    
    # Define task dependencies (ELT flow)
    extract_task >> load_task >> validate_task >> transform_group >> export_task