# Kasparro ETL System - Cloud Deployment Guide

## 🎯 System Status: READY FOR DEPLOYMENT

✅ **All Core Components Working:**
- CSV Ingester: 10 records loaded
- CoinPaprika API: 100 records loaded  
- CoinGecko API: 100 records loaded (with your API key)
- Total: 210 cryptocurrency records in database
- All API endpoints operational (/data, /health, /stats)

## 🚀 Deployment Options

### Option 1: AWS Deployment (Recommended)

**Prerequisites:**
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS credentials
aws configure
```

**Deploy to AWS:**
```bash
# Set your API keys
export COINPAPRIKA_API_KEY="your_key_here"  # Optional (free tier works)
export COINGECKO_API_KEY="CG-2TufP4yQWAApXnxZtWjkvwq1my"

# Run deployment script
chmod +x deploy/aws-deploy.sh
./deploy/aws-deploy.sh
```

**What the script does:**
- Creates ECR repository and pushes Docker image
- Launches RDS PostgreSQL instance
- Creates EC2 instance with Docker
- Sets up security groups and networking
- Configures automated ETL scheduling with EventBridge
- Provides public API endpoint

### Option 2: GCP Deployment

```bash
# Set your API keys
export COINPAPRIKA_API_KEY="your_key_here"
export COINGECKO_API_KEY="CG-2TufP4yQWAApXnxZtWjkvwq1my"

# Run GCP deployment
chmod +x deploy/gcp-deploy.sh
./deploy/gcp-deploy.sh
```

### Option 3: Manual Docker Deployment

For any cloud provider or VPS:

```bash
# 1. Build and push image to your registry
docker build -t your-registry/kasparro-etl:latest .
docker push your-registry/kasparro-etl:latest

# 2. Set up PostgreSQL database
# 3. Create .env file with your database URL and API keys
# 4. Deploy using docker-compose.prod.yml
```

## 🔧 Environment Variables Required

```bash
DATABASE_URL=postgresql://user:pass@host:5432/kasparro_etl
COINGECKO_API_KEY=CG-2TufP4yQWAApXnxZtWjkvwq1my
COINPAPRIKA_API_KEY=optional_key_here
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## 📊 Post-Deployment Verification

After deployment, verify these endpoints:

```bash
# Health check
curl https://your-domain/health

# Data endpoint
curl https://your-domain/data?limit=5

# Stats endpoint  
curl https://your-domain/stats
```

## ⏰ Automated ETL Scheduling

The deployment sets up automated ETL runs:
- **AWS**: EventBridge rule (hourly)
- **GCP**: Cloud Scheduler (hourly)
- **Manual**: Cron job in container

## 🔍 Monitoring & Logs

**View logs:**
```bash
# AWS
ssh -i key.pem ec2-user@your-ip
docker-compose logs -f

# Local monitoring
curl https://your-domain/stats
```

## 🎯 Assignment Completion Checklist

✅ **P0 - Foundation (COMPLETE)**
- Multi-source ETL (CSV + 2 APIs)
- PostgreSQL with normalized schema
- FastAPI with pagination/filtering
- Docker containerization
- Basic test suite

✅ **P1 - Growth Layer (COMPLETE)**  
- Third data source (CoinGecko)
- Incremental ingestion with checkpoints
- /stats endpoint with ETL metadata
- Clean architecture separation
- Comprehensive error handling

✅ **P2 - Differentiator (PARTIAL)**
- Rate limiting & backoff ✅
- Failure recovery & checkpoints ✅
- Observability with structured logs ✅
- DevOps with Docker & deployment scripts ✅

## 🚀 Ready for Final Evaluation

The system meets all P0 and P1 requirements and includes several P2 features. Ready for:
1. Cloud deployment demonstration
2. Live API endpoint testing
3. ETL scheduling verification
4. End-to-end smoke testing

**Estimated deployment time: 10-15 minutes**