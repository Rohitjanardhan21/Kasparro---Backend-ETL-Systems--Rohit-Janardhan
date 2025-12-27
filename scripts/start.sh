#!/bin/bash

# Kasparro ETL System Startup Script

echo "Starting Kasparro ETL System..."

# Wait for database to be ready
echo "Waiting for database connection..."
until python -c "from core.database import check_db_connection; exit(0 if check_db_connection() else 1)"; do
    echo "Database not ready, waiting 5 seconds..."
    sleep 5
done

echo "Database connection established!"

# Initialize database tables
echo "Initializing database tables..."
python -c "from core.database import init_db; init_db()"

# Start cron daemon
echo "Starting cron daemon..."
cron

# Run initial ETL to populate data
echo "Running initial ETL process..."
python -m ingestion.main || echo "Initial ETL failed, continuing with API startup..."

# Start the API server
echo "Starting API server..."
exec python -m api.main