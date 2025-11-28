# 🌍 Earthquake ELT Pipeline for Social Impact Analysis

A comprehensive ELT (Extract-Load-Transform) data pipeline built with Apache Airflow for analyzing earthquake data in Mexico, demonstrating the power of modern data engineering for disaster preparedness and policy-making.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Social & Environmental Impact](#social--environmental-impact)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [ELT Pipeline Explanation](#elt-pipeline-explanation)
- [Dashboard Features](#dashboard-features)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## 🎯 Project Overview

This project implements a complete ELT (Extract-Load-Transform) pipeline for earthquake data analysis, showcasing:

- **Extract**: Automated data extraction from CSV sources (simulating real-time seismic data feeds)
- **Load**: Raw data loading into PostgreSQL without transformation (preserving data integrity)
- **Transform**: In-database transformations using SQL (creating analytics-ready datasets)
- **Orchestration**: Apache Airflow for workflow management and scheduling
- **Visualization**: Interactive Dash dashboard for insights and analysis

## 🌱 Social & Environmental Impact

### Real-World Problem
Mexico is located in one of the most seismically active regions in the world. Understanding earthquake patterns is crucial for:
- **Public Safety**: Early warning systems and evacuation planning
- **Infrastructure**: Building code enforcement and urban planning
- **Policy Making**: Resource allocation for disaster response
- **Research**: Understanding seismic patterns and predicting future events

### Who Benefits?
- **Civil Protection Agencies**: Data-driven emergency response planning
- **Urban Planners**: Informed decisions about construction zones
- **Policy Makers**: Evidence-based resource allocation
- **Researchers**: Historical data analysis and pattern recognition
- **Citizens**: Access to transparent seismic information

### Why ELT?
1. **Data Preservation**: Raw seismic data must be preserved exactly as received for audit trails and scientific accuracy
2. **Continuous Growth**: New earthquakes occur daily, requiring incremental data loads
3. **Evolving Analysis**: As seismology advances, new transformations can be applied to existing raw data without re-extraction
4. **Performance**: In-database transformations leverage PostgreSQL's power for large-scale aggregations
5. **Flexibility**: Data scientists can create new features from raw data without affecting production pipelines

## 🏗️ Architecture

```
┌─────────────────┐
│  CSV Data       │
│  (Sismos.csv)   │
└────────┬────────┘
         │ EXTRACT
         ▼
┌─────────────────┐
│  Raw Data       │
│  (Parquet)      │
└────────┬────────┘
         │ LOAD (No Transform!)
         ▼
┌─────────────────┐
│  PostgreSQL     │
│  raw_earthquakes│ ◄─── Immutable raw data
└────────┬────────┘
         │ TRANSFORM (In-Database SQL)
         ▼
┌─────────────────┐
│  PostgreSQL     │
│analytics_earth..│ ◄─── Cleaned & enriched
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Dash Dashboard │
│  (Visualizations)│
└─────────────────┘
```

### Data Flow
1. **Airflow Scheduler** triggers DAG daily
2. **Extract Task** reads CSV and saves to Parquet
3. **Load Task** inserts raw data into PostgreSQL (no transformation)
4. **Validate Task** ensures data integrity
5. **Transform Tasks** clean and enrich data using SQL
6. **Export Task** creates Parquet files for dashboard
7. **Dashboard** reads from analytics layer only

## 🛠️ Technology Stack

- **Orchestration**: Apache Airflow 2.7.3
- **Database**: PostgreSQL 13
- **Data Processing**: Pandas, SQLAlchemy
- **Storage**: Parquet (columnar format)
- **Dashboard**: Dash, Plotly
- **Containerization**: Docker, Docker Compose
- **Language**: Python 3.10

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available
- Git (for cloning)

### Step 1: Clone and Setup
```bash
# Clone repository
git clone <your-repo-url>
cd earthquake-elt-pipeline

# Create data directories
mkdir -p data/raw data/analytics

# Place your Sismos.csv in the data/ folder
cp /path/to/Sismos.csv data/
```

### Step 2: Start Services
```bash
# Build and start all services
docker-compose up -d

# Wait for initialization (2-3 minutes)
docker-compose logs -f airflow-init
```

### Step 3: Access Applications
- **Airflow UI**: http://localhost:8080
  - Username: `admin`
  - Password: `admin`
- **Dashboard**: http://localhost:8050
- **PostgreSQL**: `localhost:5432`
  - User: `dwuser`
  - Password: `dwpassword`
  - Database: `earthquake_dw`

### Step 4: Run the Pipeline
1. Open Airflow UI (http://localhost:8080)
2. Enable the `earthquake_elt_pipeline` DAG
3. Click "Trigger DAG" to run manually
4. Monitor execution in Graph or Tree view
5. Once complete, check the dashboard at http://localhost:8050

### Step 5: Stop Services
```bash
# Stop all services
docker-compose down

# Remove all data (careful!)
docker-compose down -v
```

## 📁 Project Structure

```
earthquake-elt-pipeline/
├── dags/
│   └── earthquake_elt_dag.py      # Main ELT pipeline DAG
├── dashboard/
│   └── app.py                      # Dash dashboard application
├── data/
│   ├── raw/                        # Raw Parquet files (partitioned)
│   ├── analytics/                  # Transformed Parquet files
│   └── Sismos.csv                  # Source data (place here)
├── config/
│   └── init_db.sql                 # Database initialization
├── docs/
│   ├── JUSTIFICATION.md            # Social impact justification
│   └── SETUP.md                    # Detailed setup guide
├── logs/                           # Airflow logs
├── plugins/                        # Custom Airflow plugins
├── docker-compose.yml              # Multi-container orchestration
├── Dockerfile                      # Custom Airflow image
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables
└── README.md                       # This file
```

## 🔄 ELT Pipeline Explanation

### What is ELT?
**ELT** (Extract-Load-Transform) differs from **ETL** (Extract-Transform-Load) in the order of operations:

| Step | ETL | ELT |
|------|-----|-----|
| Extract | ✅ Get data | ✅ Get data |
| Transform | ✅ Clean BEFORE load | ❌ NOT here |
| Load | ✅ Load clean data | ✅ Load RAW data |
| Transform | ❌ Already done | ✅ Transform AFTER load |

### Why ELT for Earthquakes?

1. **Immutable Raw Data**
   - Original seismic readings must never be modified
   - Enables re-analysis with improved algorithms
   - Provides audit trail for scientific research

2. **Performance**
   - PostgreSQL can transform millions of rows faster than Python
   - In-database aggregations leverage indexes and query optimization
   - Parallel processing within the database

3. **Flexibility**
   - New transformations don't require re-extraction
   - Data scientists can experiment without affecting raw data
   - Easy to add new features or fix transformation bugs

4. **Scalability**
   - Raw data can be partitioned by date
   - Incremental loads only process new data
   - Analytics layer can be rebuilt from raw at any time

### Pipeline Stages

#### 1. Extract (Python)
```python
# Read CSV and save to Parquet
df = pd.read_csv('Sismos.csv')
df.to_parquet(f'raw/earthquakes_{batch_id}.parquet')
```

#### 2. Load (Python → PostgreSQL)
```python
# Load raw data WITHOUT transformation
df.to_sql('raw_earthquakes', engine, if_exists='append')
# All columns remain as TEXT - no type conversion!
```

#### 3. Transform (SQL in PostgreSQL)
```sql
-- Clean and transform INSIDE the database
INSERT INTO analytics_earthquakes
SELECT 
    TO_DATE(fecha_utc, 'DD/MM/YYYY') as earthquake_date,
    CAST(magnitud AS NUMERIC) as magnitude,
    -- Feature engineering
    CASE 
        WHEN magnitude >= 6.0 THEN 'Major'
        WHEN magnitude >= 4.0 THEN 'Moderate'
        ELSE 'Minor'
    END as magnitude_category
FROM raw_earthquakes;
```

### Key Features

✅ **Error Handling**
- 3 automatic retries with exponential backoff
- Validation tasks to ensure data quality
- Comprehensive logging

✅ **Scaling**
- Parquet format for efficient storage
- Partitioned raw data by batch
- In-database SQL transformations
- Indexes on key columns

✅ **Scheduling**
- Daily execution (@daily schedule)
- Catchup disabled for production
- Configurable intervals

## 📊 Dashboard Features

### KPIs
- **Total Earthquakes**: Historical count
- **Average Magnitude**: Central tendency
- **Significant Events**: High-risk earthquakes (≥5.0 magnitude)
- **Maximum Magnitude**: Highest recorded

### Visualizations
1. **Magnitude Distribution**: Bar chart showing earthquake intensity categories
2. **Regional Analysis**: Top 10 most seismically active regions
3. **Temporal Patterns**: Time series of earthquake frequency
4. **Geographic Map**: Interactive map with magnitude/location
5. **Depth Analysis**: Distribution by depth category

### Filters
- Magnitude range slider
- Region multi-select dropdown
- Auto-refresh every minute

### Insights
- Most active regions
- Depth patterns
- Risk assessment recommendations

## 🔧 Development

### Adding New Transformations

1. Edit `dags/earthquake_elt_dag.py`
2. Add new SQL in `TRANSFORM_SQL` constant
3. Raw data remains unchanged
4. Test with `docker-compose restart airflow-scheduler`

### Customizing Dashboard

1. Edit `dashboard/app.py`
2. Add new queries to fetch different aggregations
3. Create new Plotly charts
4. Restart: `docker-compose restart dashboard`

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U dwuser -d earthquake_dw

# View raw data
SELECT * FROM raw_earthquakes LIMIT 10;

# View transformed data
SELECT * FROM analytics_earthquakes LIMIT 10;

# Check statistics
SELECT * FROM earthquake_statistics;
```

## 🐛 Troubleshooting

### Airflow won't start
```bash
# Check logs
docker-compose logs airflow-webserver
docker-compose logs airflow-scheduler

# Restart services
docker-compose restart
```

### Dashboard shows no data
```bash
# Verify pipeline ran successfully
# Check Airflow UI for task status

# Verify data in database
docker-compose exec postgres psql -U dwuser -d earthquake_dw -c "SELECT COUNT(*) FROM analytics_earthquakes;"
```

### Database connection errors
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres pg_isready -U dwuser
```

### Performance issues
```bash
# Check resource usage
docker stats

# Increase Docker memory allocation
# Edit Docker Desktop settings → Resources → Memory
```

## 📚 Additional Resources

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Dash Documentation](https://dash.plotly.com/)
- [Parquet Format](https://parquet.apache.org/)

## 👥 Contributors

- Data Engineering Team
- Social Impact Analysis Group

## 📄 License

This project is for educational purposes.

---

**Built with ❤️ for disaster preparedness and social impact**