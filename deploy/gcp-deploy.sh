#!/bin/bash

# GCP Deployment Script for Kasparro ETL System
# This script deploys the system to Google Cloud Platform

set -e

echo "🚀 Starting GCP deployment for Kasparro ETL System..."

# Configuration
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-us-central1}
ZONE=${ZONE:-us-central1-a}
INSTANCE_NAME=${INSTANCE_NAME:-kasparro-etl-instance}
DB_INSTANCE_NAME=${DB_INSTANCE_NAME:-kasparro-etl-db}

# Check if gcloud CLI is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install it first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Enable required APIs
echo "🔧 Enabling required GCP APIs..."
gcloud services enable compute.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudscheduler.googleapis.com

# Build and push Docker image to Container Registry
echo "📦 Building and pushing Docker image..."

IMAGE_NAME="gcr.io/${PROJECT_ID}/kasparro-etl:latest"

# Build image
docker build -t $IMAGE_NAME .

# Configure Docker for GCR
gcloud auth configure-docker

# Push image
docker push $IMAGE_NAME

echo "✅ Docker image pushed to GCR: $IMAGE_NAME"

# Create Cloud SQL instance
echo "🗄️ Creating Cloud SQL PostgreSQL instance..."

DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

gcloud sql instances create $DB_INSTANCE_NAME \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --storage-type=SSD \
    --storage-size=20GB \
    --backup-start-time=03:00 \
    --enable-bin-log \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04 \
    --maintenance-release-channel=production 2>/dev/null || echo "Cloud SQL instance already exists"

# Set root password
gcloud sql users set-password postgres \
    --instance=$DB_INSTANCE_NAME \
    --password=$DB_PASSWORD

# Create database
gcloud sql databases create kasparro_etl \
    --instance=$DB_INSTANCE_NAME 2>/dev/null || echo "Database already exists"

# Get Cloud SQL connection name
SQL_CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE_NAME --format="value(connectionName)")

echo "✅ Cloud SQL instance created: $SQL_CONNECTION_NAME"

# Create firewall rule
echo "🔒 Creating firewall rules..."

gcloud compute firewall-rules create kasparro-etl-allow-http \
    --allow tcp:80,tcp:8000 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow HTTP traffic for Kasparro ETL" 2>/dev/null || echo "Firewall rule already exists"

# Create startup script
cat > startup-script.sh << EOF
#!/bin/bash

# Update system
apt-get update
apt-get install -y docker.io docker-compose curl

# Start Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker \$USER

# Install Cloud SQL Proxy
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy
chmod +x cloud_sql_proxy
mv cloud_sql_proxy /usr/local/bin/

# Create application directory
mkdir -p /app
cd /app

# Create environment file
cat > .env << EOL
DATABASE_URL=postgresql://postgres:$DB_PASSWORD@127.0.0.1:5432/kasparro_etl
COINPAPRIKA_API_KEY=\${COINPAPRIKA_API_KEY}
COINGECKO_API_KEY=\${COINGECKO_API_KEY}
ENVIRONMENT=production
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
EOL

# Create docker-compose file
cat > docker-compose.yml << EOL
version: '3.8'
services:
  cloud-sql-proxy:
    image: gcr.io/cloudsql-docker/gce-proxy:1.33.2
    command: /cloud_sql_proxy -instances=$SQL_CONNECTION_NAME=tcp:0.0.0.0:5432
    ports:
      - "5432:5432"
    restart: unless-stopped

  app:
    image: $IMAGE_NAME
    ports:
      - "80:8000"
    env_file:
      - .env
    depends_on:
      - cloud-sql-proxy
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
EOL

# Create directories
mkdir -p data logs

# Configure Docker for GCR
gcloud auth configure-docker

# Start the application
docker-compose up -d

# Setup cron for ETL
echo "0 * * * * cd /app && docker-compose exec -T app python -m ingestion.main >> /app/logs/etl-cron.log 2>&1" | crontab -

# Setup log rotation
cat > /etc/logrotate.d/kasparro-etl << EOL
/app/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOL
EOF

# Create Compute Engine instance
echo "🖥️ Creating Compute Engine instance..."

gcloud compute instances create $INSTANCE_NAME \
    --zone=$ZONE \
    --machine-type=e2-medium \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --boot-disk-type=pd-standard \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --metadata-from-file startup-script=startup-script.sh \
    --tags=kasparro-etl-server 2>/dev/null || echo "Instance already exists"

# Wait for instance to be running
echo "⏳ Waiting for instance to be ready..."
sleep 60

# Get external IP
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)")

echo "✅ Compute Engine instance created: $INSTANCE_NAME"
echo "🌐 External IP: $EXTERNAL_IP"

# Create Cloud Scheduler job for ETL
echo "⏰ Setting up scheduled ETL with Cloud Scheduler..."

# Create service account for Cloud Scheduler
gcloud iam service-accounts create kasparro-etl-scheduler \
    --description="Service account for Kasparro ETL Cloud Scheduler" \
    --display-name="Kasparro ETL Scheduler" 2>/dev/null || echo "Service account already exists"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:kasparro-etl-scheduler@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/compute.instanceAdmin.v1"

# Create Cloud Scheduler job
gcloud scheduler jobs create http kasparro-etl-hourly \
    --schedule="0 * * * *" \
    --uri="http://${EXTERNAL_IP}:8000/api/v1/etl/trigger" \
    --http-method=POST \
    --description="Hourly ETL execution for Kasparro system" \
    --time-zone="UTC" 2>/dev/null || echo "Scheduler job already exists"

echo "✅ Cloud Scheduler job created for hourly ETL execution"

# Setup monitoring (optional)
echo "📊 Setting up basic monitoring..."

# Create uptime check
gcloud monitoring uptime create kasparro-etl-uptime \
    --display-name="Kasparro ETL API Uptime" \
    --http-check-path="/health" \
    --hostname=$EXTERNAL_IP \
    --port=80 \
    --period=300 2>/dev/null || echo "Uptime check already exists"

# Clean up
rm -f startup-script.sh

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Deployment Summary:"
echo "   • Project ID: $PROJECT_ID"
echo "   • Instance Name: $INSTANCE_NAME"
echo "   • External IP: $EXTERNAL_IP"
echo "   • Cloud SQL Instance: $SQL_CONNECTION_NAME"
echo "   • Container Image: $IMAGE_NAME"
echo "   • API URL: http://$EXTERNAL_IP"
echo "   • Health Check: http://$EXTERNAL_IP/health"
echo ""
echo "🔑 SSH Access:"
echo "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "📝 Next Steps:"
echo "   1. Set your API keys in the instance environment"
echo "   2. Test the API endpoints"
echo "   3. Monitor logs and metrics in Cloud Console"
echo "   4. Set up additional alerting (optional)"
echo ""
echo "⚠️  Important: Save the database password: $DB_PASSWORD"
echo ""
echo "🔍 Useful Commands:"
echo "   • View logs: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='cd /app && docker-compose logs'"
echo "   • Restart services: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='cd /app && docker-compose restart'"
echo "   • Check status: curl http://$EXTERNAL_IP/health"