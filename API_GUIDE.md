# Kasparro ETL System - API Integration Guide

## 🌐 External API Integrations

This system integrates with two major cryptocurrency data APIs to provide comprehensive market data.

### CoinPaprika API

**Base URL**: `https://api.coinpaprika.com/v1`

#### Features
- **Free Tier**: Unlimited requests, no API key required
- **Pro Tier**: API key provides additional features and guaranteed uptime
- **Data Coverage**: 3000+ cryptocurrencies, market data, historical prices

#### Endpoints Used
- `GET /tickers` - Get market data for all cryptocurrencies

#### Authentication
```bash
# Free tier (no key required)
curl "https://api.coinpaprika.com/v1/tickers?limit=10"

# Pro tier (with API key)
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://api.coinpaprika.com/v1/tickers?limit=10"
```

#### Rate Limits
- **Free Tier**: No official limit (fair use policy)
- **Pro Tier**: Higher guaranteed limits

#### Sample Response
```json
[
  {
    "id": "btc-bitcoin",
    "name": "Bitcoin",
    "symbol": "BTC",
    "rank": 1,
    "quotes": {
      "USD": {
        "price": 43250.50,
        "volume_24h": 25000000000,
        "market_cap": 850000000000,
        "percent_change_1h": 0.12,
        "percent_change_24h": 2.34,
        "percent_change_7d": -1.23
      }
    }
  }
]
```

### CoinGecko API

**Base URL**: `https://api.coingecko.com/api/v3`

#### Features
- **Free Tier**: 10-50 calls/minute, no API key required
- **Demo Tier**: 500 calls/minute with API key
- **Pro Tier**: Higher limits and additional features

#### Endpoints Used
- `GET /coins/markets` - Get market data with pagination

#### Authentication
```bash
# Free tier (no key required)
curl "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page=10"

# Demo/Pro tier (with API key)
curl -H "x-cg-demo-api-key: YOUR_API_KEY" \
     "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page=10"
```

#### Rate Limits
- **Free Tier**: 10-50 calls/minute
- **Demo Tier**: 500 calls/minute
- **Pro Tier**: 10,000+ calls/minute

#### Sample Response
```json
[
  {
    "id": "bitcoin",
    "symbol": "btc",
    "name": "Bitcoin",
    "current_price": 43250.50,
    "market_cap": 850000000000,
    "market_cap_rank": 1,
    "total_volume": 25000000000,
    "high_24h": 44000,
    "low_24h": 42500,
    "price_change_24h": 1000.50,
    "price_change_percentage_24h": 2.34,
    "circulating_supply": 19500000,
    "total_supply": 21000000,
    "max_supply": 21000000
  }
]
```

## 🔧 System API Endpoints

### Base URL
- **Local**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

### Authentication
No authentication required for read-only endpoints.

### Endpoints

#### GET /
Root endpoint with API information.

```bash
curl http://localhost:8000/
```

#### GET /health
System health check with database connectivity and ETL status.

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "database_connected": true,
  "etl_last_run": {
    "run_id": "coinpaprika_20240101_120000_abc123",
    "source": "coinpaprika",
    "status": "completed",
    "records_processed": 100
  },
  "version": "1.0.0"
}
```

#### GET /health/detailed
Comprehensive system diagnostics.

```bash
curl http://localhost:8000/health/detailed
```

#### GET /data
Paginated cryptocurrency data with filtering.

**Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Records per page (default: 100, max: 1000)
- `source` (string): Filter by source (`coinpaprika`, `coingecko`, `csv`)
- `coin_id` (string): Filter by coin ID (partial match)
- `symbol` (string): Filter by symbol (partial match)

```bash
# Get first 10 records
curl "http://localhost:8000/data?limit=10"

# Filter by source
curl "http://localhost:8000/data?source=coinpaprika&limit=5"

# Search by symbol
curl "http://localhost:8000/data?symbol=BTC"
```

**Response:**
```json
{
  "data": [
    {
      "id": "uuid-here",
      "coin_id": "bitcoin",
      "name": "Bitcoin",
      "symbol": "BTC",
      "price_usd": 43250.50,
      "market_cap_usd": 850000000000,
      "volume_24h_usd": 25000000000,
      "rank": 1,
      "percent_change_24h": 2.34,
      "source": "coinpaprika",
      "processed_at": "2024-01-01T12:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total_records": 1500,
    "total_pages": 150,
    "has_next": true,
    "has_prev": false
  },
  "metadata": {
    "request_id": "req-uuid-here",
    "api_latency_ms": 45.67,
    "records_returned": 10
  }
}
```

#### GET /data/summary
Data summary and statistics.

```bash
curl http://localhost:8000/data/summary
```

#### GET /stats
ETL run statistics and summaries.

```bash
curl http://localhost:8000/stats
```

**Response:**
```json
{
  "total_runs": 25,
  "successful_runs": 23,
  "failed_runs": 2,
  "last_successful_run": {
    "run_id": "coinpaprika_20240101_120000_abc123",
    "source": "coinpaprika",
    "end_time": "2024-01-01T12:05:00Z",
    "duration_seconds": 300.5,
    "records_processed": 100
  },
  "records_by_source": {
    "coinpaprika": 500,
    "coingecko": 750,
    "csv": 250
  },
  "avg_duration_seconds": 285.3
}
```

#### GET /stats/runs
Detailed ETL run information with filtering.

**Parameters:**
- `limit` (int): Number of runs to return (default: 50, max: 1000)
- `source` (string): Filter by source
- `status` (string): Filter by status (`running`, `completed`, `failed`)

```bash
# Get recent runs
curl "http://localhost:8000/stats/runs?limit=10"

# Filter by source and status
curl "http://localhost:8000/stats/runs?source=coinpaprika&status=completed"
```

#### GET /stats/performance
Performance analytics for specified time window.

**Parameters:**
- `hours` (int): Time window in hours (default: 24, max: 168)

```bash
# Last 24 hours performance
curl "http://localhost:8000/stats/performance"

# Last week performance
curl "http://localhost:8000/stats/performance?hours=168"
```

## 🔍 Interactive Documentation

### Swagger UI
Visit `http://localhost:8000/docs` for interactive API documentation with:
- Complete endpoint documentation
- Request/response schemas
- Try-it-out functionality
- Authentication examples

### ReDoc
Visit `http://localhost:8000/redoc` for alternative documentation with:
- Clean, readable format
- Detailed schema documentation
- Code examples in multiple languages

## 🧪 Testing APIs

### Test External API Connectivity
```bash
# Test both CoinPaprika and CoinGecko APIs
python scripts/test_apis.py

# With API keys
export COINPAPRIKA_API_KEY=your_key
export COINGECKO_API_KEY=your_key
python scripts/test_apis.py
```

### Test System APIs
```bash
# Quick end-to-end test
python scripts/quick_test.py

# Or use curl
curl http://localhost:8000/health
curl http://localhost:8000/data?limit=5
```

## 🚨 Error Handling

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Internal Server Error

### Error Response Format
```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR",
  "request_id": "req-uuid-here"
}
```

### Common Errors

#### Invalid Parameters
```bash
curl "http://localhost:8000/data?page=0"
# Returns 422: page must be >= 1
```

#### Invalid Source Filter
```bash
curl "http://localhost:8000/data?source=invalid"
# Returns 400: Source must be one of: coinpaprika, coingecko, csv
```

## 📊 Rate Limiting

### External APIs
- **CoinPaprika**: No official limits (free tier)
- **CoinGecko**: 10-50 calls/minute (free tier)

### System Implementation
- Configurable rate limiting per source
- Exponential backoff with jitter
- Automatic retry logic
- Rate limit status in logs

### Configuration
```bash
# Environment variables
ETL_RATE_LIMIT_REQUESTS=100    # Requests per period
ETL_RATE_LIMIT_PERIOD=60       # Period in seconds
ETL_RETRY_ATTEMPTS=3           # Max retry attempts
ETL_RETRY_DELAY=5              # Base delay in seconds
```

## 🔐 Security

### API Keys
- Store in environment variables
- Never commit to version control
- Use different keys for different environments
- Monitor usage and rotate regularly

### Input Validation
- All inputs validated with Pydantic
- SQL injection protection via SQLAlchemy
- Request size limits
- Parameter validation

### CORS
- Configured for development (allow all origins)
- Restrict origins in production
- Proper headers for security

## 📈 Monitoring

### Health Checks
- Database connectivity
- ETL process status
- API response times
- System resources

### Logging
- Structured JSON logs
- Request correlation IDs
- Performance metrics
- Error tracking

### Metrics
- ETL success/failure rates
- API response times
- Data processing throughput
- Error patterns

## 🚀 Production Deployment

### Environment Variables
```bash
# Required
DATABASE_URL=postgresql://user:pass@host:port/db

# Optional (for higher rate limits)
COINPAPRIKA_API_KEY=your_key
COINGECKO_API_KEY=your_key

# Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
```

### Cloud Deployment
- AWS: Use provided deployment script
- GCP: Use provided deployment script
- Azure: Manual setup instructions available
- Docker: Production-ready containers

### Scaling Considerations
- Database connection pooling
- API rate limit management
- Load balancer configuration
- Horizontal scaling support