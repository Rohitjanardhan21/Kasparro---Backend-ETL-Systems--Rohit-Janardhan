# Kasparro Backend & ETL System

A production-grade backend system with ETL pipelines for cryptocurrency data ingestion and API services.

## Architecture Overview

This system implements a multi-source ETL pipeline that ingests data from:
- CoinPaprika API (cryptocurrency market data)
- CoinGecko API (cryptocurrency prices and market info)
- CSV files (historical data)

The data is processed, normalized, and stored in PostgreSQL with a clean API layer for data access.

## Quick Start

```bash
# Start the entire system
make up

# Run tests
make test

# Stop the system
make down
```

## System Components

### ETL Pipeline (`ingestion/`)
- Multi-source data ingestion with incremental processing
- Schema normalization and validation using Pydantic
- Checkpoint-based recovery system
- Rate limiting and retry logic

### API Service (`api/`)
- RESTful endpoints with pagination and filtering
- Health checks and system status
- ETL statistics and monitoring
- Request tracking and performance metrics

### Core Services (`services/`)
- Database connection management
- Configuration handling
- Logging and monitoring utilities

## API Endpoints

- `GET /data` - Paginated data access with filtering
- `GET /health` - System health and connectivity status
- `GET /stats` - ETL run statistics and metadata

## API Keys Setup

### CoinPaprika API
1. Visit [CoinPaprika API](https://coinpaprika.com/api/)
2. **Free Tier**: No API key required - unlimited requests
3. **Pro Tier**: Sign up for API key for additional features
4. Add to `.env`: `COINPAPRIKA_API_KEY=your_key_here` (optional)

### CoinGecko API  
1. Visit [CoinGecko API](https://www.coingecko.com/en/api)
2. **Free Tier**: No API key required - 10-50 calls/minute
3. **Demo/Pro Tier**: Sign up for API key for higher rate limits
4. Add to `.env`: `COINGECKO_API_KEY=your_key_here` (optional)

### Testing APIs
```bash
# Test API connectivity (works without keys)
python scripts/test_apis.py

# Test with your API keys
export COINPAPRIKA_API_KEY=your_key
export COINGECKO_API_KEY=your_key
python scripts/test_apis.py
```

## Testing

The system includes comprehensive tests covering:
- ETL transformation logic
- Incremental ingestion
- API endpoints
- Failure scenarios
- Schema validation

## Cloud Deployment

The system is designed for cloud deployment with:
- Docker containerization
- Scheduled ETL runs via cron
- Cloud-native logging and monitoring
- Health checks and auto-recovery

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run ETL manually
python -m ingestion.main

# Start API server
python -m api.main

# Run specific tests
pytest tests/test_etl.py -v
```