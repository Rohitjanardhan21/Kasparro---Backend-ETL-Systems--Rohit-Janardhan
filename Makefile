.PHONY: up down test clean logs build

# Start the entire system
up:
	@echo "Starting Kasparro ETL System..."
	docker-compose up --build -d
	@echo "System started! API available at http://localhost:8000"
	@echo "Health check: http://localhost:8000/health"

# Stop the system
down:
	@echo "Stopping Kasparro ETL System..."
	docker-compose down

# Run tests
test:
	@echo "Running test suite..."
	docker-compose exec app pytest tests/ -v --tb=short

# Test API connectivity (without database)
test-apis:
	@echo "Testing API connectivity..."
	python scripts/test_apis.py

# Quick end-to-end test
test-quick:
	@echo "Running quick system test..."
	python scripts/quick_test.py

# Run tests with coverage
test-coverage:
	docker-compose exec app pytest tests/ --cov=. --cov-report=html --cov-report=term

# Build without starting
build:
	docker-compose build

# View logs
logs:
	docker-compose logs -f

# View app logs only
logs-app:
	docker-compose logs -f app

# Clean up everything
clean:
	docker-compose down -v
	docker system prune -f

# Run ETL manually
etl:
	docker-compose exec app python -m ingestion.main

# Access database
db:
	docker-compose exec db psql -U postgres -d kasparro_etl

# Install dependencies locally (for development)
install:
	pip install -r requirements.txt

# Format code
format:
	docker-compose exec app black .
	docker-compose exec app isort .

# Lint code
lint:
	docker-compose exec app flake8 .
	docker-compose exec app mypy .

# Shell access
shell:
	docker-compose exec app bash

# Reset database
reset-db:
	docker-compose down -v
	docker-compose up -d db
	sleep 10
	docker-compose up -d app