#!/bin/bash
# Setup Airflow connection to Data Warehouse

docker-compose exec airflow-webserver airflow connections add 'earthquake_dw' \
    --conn-type 'postgres' \
    --conn-login 'dwuser' \
    --conn-password 'dwpassword' \
    --conn-host 'postgres' \
    --conn-port '5432' \
    --conn-schema 'earthquake_dw'

echo "Connection 'earthquake_dw' created successfully!"
