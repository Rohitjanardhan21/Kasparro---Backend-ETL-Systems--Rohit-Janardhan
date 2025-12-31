#!/bin/bash

# Quick deployment using Docker Hub
echo "🐳 Docker Hub Deployment for Kasparro ETL"
echo "========================================"

# Step 1: Build and push to Docker Hub
echo "📦 Building and pushing to Docker Hub..."

# Build the image
docker build -t kasparro-etl:latest .

# Tag for Docker Hub (replace 'yourusername' with your Docker Hub username)
DOCKER_USERNAME=${DOCKER_USERNAME:-yourusername}
docker tag kasparro-etl:latest $DOCKER_USERNAME/kasparro-etl:latest

echo "🔐 Please login to Docker Hub:"
docker login

echo "📤 Pushing to Docker Hub..."
docker push $DOCKER_USERNAME/kasparro-etl:latest

echo "✅ Image pushed to Docker Hub: $DOCKER_USERNAME/kasparro-etl:latest"

# Step 2: Create deployment script for cloud server
cat > cloud-deploy.sh << EOF
#!/bin/bash

# Run this script on your cloud server
echo "🚀 Deploying Kasparro ETL from Docker Hub..."

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker \$USER
    echo "Please log out and back in, then run this script again"
    exit 1
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Create app directory
mkdir -p /app && cd /app

# Create docker-compose.yml with your Docker Hub image
cat > docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: kasparro_etl
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: \${POSTGRES_PASSWORD:-secure_db_password}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  app:
    image: $DOCKER_USERNAME/kasparro-etl:latest
    ports:
      - "80:8000"
      - "8080:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:\${POSTGRES_PASSWORD:-secure_db_password}@db:5432/kasparro_etl
      - COINGECKO_API_KEY=\${COINGECKO_API_KEY}
      - COINPAPRIKA_API_KEY=
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
COMPOSE_EOF

# Create directories
mkdir -p data logs

# Pull and start the application
echo "🚀 Starting application..."
docker-compose pull
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Test the deployment
echo "🧪 Testing deployment..."
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ Health endpoint: OK"
else
    echo "❌ Health endpoint: FAILED"
    echo "Check logs: docker-compose logs app"
    exit 1
fi

if curl -f "http://localhost/data?limit=1" > /dev/null 2>&1; then
    echo "✅ Data endpoint: OK"
else
    echo "❌ Data endpoint: FAILED"
fi

# Set up cron job
echo "⏰ Setting up automated ETL..."
echo "0 * * * * cd /app && /usr/local/bin/docker-compose exec -T app python -m ingestion.main >> /app/logs/etl-cron.log 2>&1" | crontab -

echo ""
echo "🎉 Deployment completed successfully!"
echo "=================================="
echo "API Endpoints:"
echo "  • Health: http://\$(curl -s ifconfig.me)/health"
echo "  • Data:   http://\$(curl -s ifconfig.me)/data"
echo "  • Stats:  http://\$(curl -s ifconfig.me)/stats"
echo ""
echo "📊 Monitor with:"
echo "  docker-compose logs -f app"
echo "  docker-compose ps"
echo ""
EOF

chmod +x cloud-deploy.sh

echo ""
echo "🎯 Next Steps:"
echo "============="
echo "1. Copy 'cloud-deploy.sh' to your cloud server"
echo "2. Run it on your server: bash cloud-deploy.sh"
echo "3. Your API will be available at http://YOUR_SERVER_IP"
echo ""
echo "📋 Files created:"
echo "  • cloud-deploy.sh (run this on your cloud server)"
echo ""
echo "🐳 Docker Hub image: $DOCKER_USERNAME/kasparro-etl:latest"