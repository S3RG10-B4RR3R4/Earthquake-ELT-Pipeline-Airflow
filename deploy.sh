#!/bin/bash

echo "��� Earthquake ELT Pipeline - Deployment Script"
echo "=============================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/7] Checking prerequisites...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker Desktop.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found. Please install Docker Compose.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose found${NC}"

# Step 2: Check for CSV file
echo -e "${YELLOW}[2/7] Checking for data file...${NC}"
if [ ! -f "data/raw/Sismos.csv" ]; then
    echo -e "${RED}❌ Sismos.csv not found in data/ directory${NC}"
    echo "Please place your CSV file in the data/ directory"
    exit 1
fi
echo -e "${GREEN}✅ Sismos.csv found${NC}"

# Step 3: Create directories
echo -e "${YELLOW}[3/7] Creating directories...${NC}"
mkdir -p data/raw data/analytics logs
echo -e "${GREEN}✅ Directories created${NC}"

# Step 4: Build images
echo -e "${YELLOW}[4/7] Building Docker images (this may take a few minutes)...${NC}"
docker-compose build
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Images built successfully${NC}"

# Step 5: Start services
echo -e "${YELLOW}[5/7] Starting services...${NC}"
docker-compose up -d
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to start services${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Services started${NC}"

# Step 6: Wait for services to be healthy
echo -e "${YELLOW}[6/7] Waiting for services to be ready (this may take 2-3 minutes)...${NC}"
sleep 30

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
until docker-compose exec -T postgres pg_isready -U dwuser > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo -e "\n${GREEN}✅ PostgreSQL ready${NC}"

# Wait for Airflow webserver
echo "Waiting for Airflow webserver..."
until curl -s http://localhost:8080/health > /dev/null 2>&1; do
    echo -n "."
    sleep 5
done
echo -e "\n${GREEN}✅ Airflow webserver ready${NC}"

# Step 7: Setup Airflow connection
echo -e "${YELLOW}[7/7] Setting up Airflow connection...${NC}"
bash config/setup_airflow_connection.sh
echo -e "${GREEN}✅ Connection configured${NC}"

# Final status
echo ""
echo "=============================================="
echo -e "${GREEN}��� Deployment Complete!${NC}"
echo "=============================================="
echo ""
echo "��� Access Points:"
echo "   Airflow UI:  http://localhost:8080"
echo "   Dashboard:   http://localhost:8050"
echo "   PostgreSQL:  localhost:5432"
echo ""
echo "��� Credentials:"
echo "   Airflow - user: admin, pass: admin"
echo "   PostgreSQL - user: dwuser, pass: dwpassword"
echo ""
echo "▶️  Next Steps:"
echo "   1. Open http://localhost:8080 in your browser"
echo "   2. Login with admin/admin"
echo "   3. Enable the 'earthquake_elt_pipeline' DAG"
echo "   4. Click 'Trigger DAG' to run the pipeline"
echo "   5. Open http://localhost:8050 to view the dashboard"
echo ""
echo "��� Monitor logs:"
echo "   docker-compose logs -f"
echo ""
echo "��� Stop services:"
echo "   docker-compose down"
echo ""
