# Complete Setup Guide

## Prerequisites

### System Requirements
- **OS**: Linux, macOS, or Windows (with WSL2)
- **RAM**: Minimum 4GB, recommended 8GB
- **Disk Space**: At least 10GB free
- **CPU**: 2+ cores recommended

### Required Software
1. **Docker Desktop** (version 20.10+)
   - Download: https://www.docker.com/products/docker-desktop
   - Enable Docker Compose V2

2. **Git** (optional, for cloning)
   - Download: https://git-scm.com/downloads

3. **Text Editor** (optional)
   - VS Code, Sublime Text, or any editor

## Installation Steps

### 1. Download/Clone Project
```bash
# Option A: Clone from GitHub
git clone <your-repository-url>
cd earthquake-elt-pipeline

# Option B: Download ZIP and extract
# Then navigate to the folder
cd earthquake-elt-pipeline
```

### 2. Prepare Your Data

Place your `Sismos.csv` file in the `data/` directory:
```bash
# Copy your CSV file
cp /path/to/your/Sismos.csv data/Sismos.csv

# Verify it's there
ls -lh data/Sismos.csv
```

**CSV Format Requirements:**
- Columns: Fecha UTC, Hora UTC, Magnitud, Latitud, Longitud, Profundidad, Referencia de localizacion, Fecha local, Hora local, Estatus
- Encoding: UTF-8
- Delimiter: Comma (,)

### 3. Configure Environment (Optional)

The `.env` file is pre-configured, but you can customize:
```bash
# Edit .env file
nano .env

# Key configurations:
# - Database passwords
# - Airflow admin credentials
# - Resource limits
```

### 4. Build and Start Services
```bash
# Build Docker images (first time only)
docker-compose build

# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

**Expected Output:**
```
NAME                           STATUS              PORTS
earthquake-airflow-webserver   Up (healthy)        0.0.0.0:8080->8080/tcp
earthquake-airflow-scheduler   Up (healthy)        
earthquake-postgres            Up (healthy)        0.0.0.0:5432->5432/tcp
earthquake-dashboard           Up                  0.0.0.0:8050->8050/tcp
```

### 5. Initialize Database

The database initializes automatically, but verify:
```bash
# Check PostgreSQL logs
docker-compose logs postgres | grep "database system is ready"

# Connect to database
docker-compose exec postgres psql -U dwuser -d earthquake_dw

# Inside PostgreSQL:
\dt  # List tables (should see raw_earthquakes, analytics_earthquakes)
\q   # Quit
```

### 6. Access Airflow

1. Open browser: http://localhost:8080
2. Login:
   - Username: `admin`
   - Password: `admin`
3. Find DAG: `earthquake_elt_pipeline`
4. Enable the DAG (toggle switch)

### 7. Run the Pipeline

#### Manual Trigger (First Run)
1. Click the "Play" button (‚ñ∂) next to the DAG name
2. Click "Trigger DAG"
3. Watch the execution in "Graph" view
4. Wait for all tasks to turn green (‚úì)

#### Monitor Execution
```bash
# Watch scheduler logs
docker-compose logs -f airflow-scheduler

# Check task logs
# In Airflow UI: Click task ‚Üí View Logs
```

### 8. Access Dashboard

1. Open browser: http://localhost:8050
2. Dashboard should display earthquake visualizations
3. Interact with filters and charts

## Verification Checklist

### ‚úÖ Services Running
```bash
docker-compose ps
# All services should show "Up" or "Up (healthy)"
```

### ‚úÖ Database Populated
```bash
docker-compose exec postgres psql -U dwuser -d earthquake_dw -c "SELECT COUNT(*) FROM raw_earthquakes;"
# Should show number of records loaded
```

### ‚úÖ Analytics Created
```bash
docker-compose exec postgres psql -U dwuser -d earthquake_dw -c "SELECT COUNT(*) FROM analytics_earthquakes;"
# Should show same or fewer records (some may be filtered)
```

### ‚úÖ Parquet Files Created
```bash
ls -lh data/raw/
ls -lh data/analytics/
# Should see .parquet files
```

### ‚úÖ Dashboard Loading Data
Open http://localhost:8050 and verify:
- KPI cards show numbers
- Charts display data
- No error messages

## Common Setup Issues

### Issue 1: Port Already in Use
**Error**: `Bind for 0.0.0.0:8080 failed: port is already allocated`

**Solution**:
```bash
# Find process using port
lsof -i :8080  # macOS/Linux
netstat -ano | findstr :8080  # Windows

# Option A: Kill the process
kill -9 <PID>

# Option B: Change port in docker-compose.yml
# Edit ports: "8081:8080" instead of "8080:8080"
```

### Issue 2: Docker Out of Memory
**Error**: `Container killed due to OOM`

**Solution**:
```bash
# Increase Docker memory
# Docker Desktop ‚Üí Settings ‚Üí Resources ‚Üí Memory
# Set to at least 4GB

# Or reduce container memory in docker-compose.yml
```

### Issue 3: Database Not Initializing
**Error**: `relation "raw_earthquakes" does not exist`

**Solution**:
```bash
# Recreate database
docker-compose down -v
docker-compose up -d

# Manually run init script
docker-compose exec postgres psql -U dwuser -d earthquake_dw -f /docker-entrypoint-initdb.d/init_db.sql
```

### Issue 4: Airflow Not Starting
**Error**: `airflow command not found`

**Solution**:
```bash
# Rebuild Airflow image
docker-compose down
docker-compose build --no-cache airflow-webserver
docker-compose up -d
```

### Issue 5: CSV File Not Found
**Error**: `FileNotFoundError: /opt/airflow/data/Sismos.csv`

**Solution**:
```bash
# Verify file location
ls -la data/Sismos.csv

# Check file name (case-sensitive)
# Must be exactly: Sismos.csv

# Restart services after placing file
docker-compose restart
```

## Advanced Configuration

### Custom Schedule
Edit `dags/earthquake_elt_dag.py`:
```python
# Change this line:
schedule_interval='@daily',

# To hourly:
schedule_interval='@hourly',

# Or custom cron:
schedule_interval='0 */6 * * *',  # Every 6 hours
```

### Database Connection from External Tools
```bash
# Connection string:
postgresql://dwuser:dwpassword@localhost:5432/earthquake_dw

# DBeaver, DataGrip, pgAdmin:
Host: localhost
Port: 5432
Database: earthquake_dw
User: dwuser
Password: dwpassword
```

### Adding New Transformations
1. Edit `TRANSFORM_SQL` in `dags/earthquake_elt_dag.py`
2. Add new SQL logic
3. Restart scheduler: `docker-compose restart airflow-scheduler`
4. Trigger DAG manually to test

### Performance Tuning
```bash
# Edit docker-compose.yml

# Increase Airflow parallelism:
environment:
  AIRFLOW__CORE__PARALLELISM: 16
  AIRFLOW__CORE__DAG_CONCURRENCY: 8

# Increase PostgreSQL resources:
command: postgres -c max_connections=200 -c shared_buffers=256MB
```

## Maintenance

### Backup Data
```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U dwuser earthquake_dw > backup.sql

# Backup Parquet files
tar -czf backup_parquet.tar.gz data/
```

### Clean Up Logs
```bash
# Remove old Airflow logs (older than 30 days)
find logs/ -type f -mtime +30 -delete

# Or clear all logs
rm -rf logs/*
```

### Update Dependencies
```bash
# Update Python packages
# Edit requirements.txt, then:
docker-compose build --no-cache
docker-compose up -d
```

### Stop and Remove Everything
```bash
# Stop services
docker-compose down

# Remove volumes (deletes data!)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Production Deployment

### Security Hardening
1. Change default passwords in `.env`
2. Use environment-specific `.env.prod`
3. Enable HTTPS for Airflow and Dashboard
4. Restrict database access
5. Use secrets management (Vault, AWS Secrets Manager)

### Scaling
1. Use external PostgreSQL (AWS RDS, Cloud SQL)
2. Switch to CeleryExecutor for distributed tasks
3. Add Redis for task queue
4. Use object storage (S3, GCS) instead of local volumes

### Monitoring
1. Enable Airflow metrics
2. Set up Prometheus + Grafana
3. Configure email alerts
4. Monitor database performance

## Troubleshooting Commands
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs airflow-scheduler
docker-compose logs postgres
docker-compose logs dashboard

# Follow logs in real-time
docker-compose logs -f

# Restart specific service
docker-compose restart airflow-scheduler

# Rebuild specific service
docker-compose up -d --build airflow-webserver

# Access container shell
docker-compose exec airflow-webserver bash
docker-compose exec postgres bash

# Check container resource usage
docker stats

# Verify network connectivity
docker-compose exec airflow-scheduler ping postgres
```

## Next Steps

1. ‚úÖ Complete setup verification
2. Ì≥ä Explore the dashboard
3. Ì¥ß Customize transformations
4. Ì≥à Add new visualizations
5. Ì∫Ä Deploy to production

## Support

For issues:
1. Check logs: `docker-compose logs`
2. Review this guide's troubleshooting section
3. Consult Airflow documentation: https://airflow.apache.org/docs/
4. Open an issue on GitHub

---

**Setup complete! You're ready to analyze earthquake data for social impact. Ìºç**
