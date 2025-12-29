# Railway.app Deployment Guide

Railway.app provides reliable cloud hosting with excellent uptime for evaluation purposes.

## Quick Deploy to Railway

1. **Connect GitHub Repository**
   ```bash
   # Visit https://railway.app
   # Connect your GitHub account
   # Select repository: Kasparro---Backend-ETL-Systems--Rohit-Janardhan
   ```

2. **Environment Variables**
   Set these in Railway dashboard:
   ```
   DATABASE_URL=postgresql://postgres:password@postgres:5432/kasparro_etl
   COINGECKO_API_KEY=CG-2TufP4yQWAApXnxZtWjkvwq1my
   COINPAPRIKA_API_KEY=optional
   API_HOST=0.0.0.0
   API_PORT=8000
   LOG_LEVEL=INFO
   ENVIRONMENT=production
   ```

3. **Add PostgreSQL Service**
   - Add PostgreSQL plugin in Railway
   - Use the provided DATABASE_URL

4. **Deploy Configuration**
   Railway will automatically detect the Dockerfile and deploy.

## Alternative: Render.com Deployment

1. **Connect Repository**
   - Visit https://render.com
   - Connect GitHub repository

2. **Create Web Service**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

3. **Add PostgreSQL Database**
   - Create PostgreSQL instance
   - Use connection string in environment variables

## Heroku Deployment (Free Tier)

```bash
# Install Heroku CLI
# Login to Heroku
heroku login

# Create app
heroku create kasparro-etl-system

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Set environment variables
heroku config:set COINGECKO_API_KEY=CG-2TufP4yQWAApXnxZtWjkvwq1my
heroku config:set API_HOST=0.0.0.0
heroku config:set LOG_LEVEL=INFO

# Deploy
git push heroku main
```

## Docker Hub + Cloud Run

```bash
# Build and push to Docker Hub
docker build -t rohitjanardhan21/kasparro-etl:latest .
docker push rohitjanardhan21/kasparro-etl:latest

# Deploy to Google Cloud Run
gcloud run deploy kasparro-etl \
  --image rohitjanardhan21/kasparro-etl:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars COINGECKO_API_KEY=CG-2TufP4yQWAApXnxZtWjkvwq1my
```

These platforms provide better uptime guarantees and are more suitable for evaluation purposes.