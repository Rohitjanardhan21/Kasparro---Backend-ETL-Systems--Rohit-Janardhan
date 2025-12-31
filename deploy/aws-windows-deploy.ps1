# AWS Deployment Script for Windows PowerShell
# Kasparro ETL System

Write-Host "🚀 AWS Deployment for Kasparro ETL System (Windows)" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green

# Configuration
$AWS_REGION = if ($env:AWS_REGION) { $env:AWS_REGION } else { "us-east-1" }
$INSTANCE_TYPE = if ($env:INSTANCE_TYPE) { $env:INSTANCE_TYPE } else { "t3.medium" }
$KEY_PAIR_NAME = if ($env:KEY_PAIR_NAME) { $env:KEY_PAIR_NAME } else { "kasparro-key" }

# Check if AWS CLI is installed
try {
    $awsVersion = aws --version 2>$null
    Write-Host "✅ AWS CLI found: $awsVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CLI not found. Please install it first:" -ForegroundColor Red
    Write-Host "   Download from: https://awscli.amazonaws.com/AWSCLIV2.msi" -ForegroundColor Yellow
    Write-Host "   Then run: aws configure" -ForegroundColor Yellow
    exit 1
}

# Test AWS credentials
try {
    $identity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Host "✅ AWS credentials configured for account: $($identity.Account)" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS credentials not configured. Please run: aws configure" -ForegroundColor Red
    exit 1
}

Write-Host "📦 Getting latest Amazon Linux AMI..." -ForegroundColor Cyan

# Get latest Amazon Linux AMI
$AMI_ID = aws ec2 describe-images `
    --owners amazon `
    --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" `
    --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' `
    --output text `
    --region $AWS_REGION

Write-Host "📦 Using AMI: $AMI_ID" -ForegroundColor Cyan

# Create security group
Write-Host "🔒 Creating security group..." -ForegroundColor Cyan

try {
    $SECURITY_GROUP_ID = aws ec2 create-security-group `
        --group-name kasparro-etl-sg `
        --description "Security group for Kasparro ETL" `
        --query 'GroupId' `
        --output text `
        --region $AWS_REGION 2>$null
} catch {
    # Security group might already exist
    $SECURITY_GROUP_ID = aws ec2 describe-security-groups `
        --group-names kasparro-etl-sg `
        --query 'SecurityGroups[0].GroupId' `
        --output text `
        --region $AWS_REGION
}

Write-Host "🔒 Security group: $SECURITY_GROUP_ID" -ForegroundColor Green

# Add security group rules
Write-Host "🔓 Adding security group rules..." -ForegroundColor Cyan

aws ec2 authorize-security-group-ingress `
    --group-id $SECURITY_GROUP_ID `
    --protocol tcp --port 22 --cidr 0.0.0.0/0 `
    --region $AWS_REGION 2>$null

aws ec2 authorize-security-group-ingress `
    --group-id $SECURITY_GROUP_ID `
    --protocol tcp --port 80 --cidr 0.0.0.0/0 `
    --region $AWS_REGION 2>$null

aws ec2 authorize-security-group-ingress `
    --group-id $SECURITY_GROUP_ID `
    --protocol tcp --port 8080 --cidr 0.0.0.0/0 `
    --region $AWS_REGION 2>$null

# Create key pair if needed
Write-Host "🔑 Checking key pair..." -ForegroundColor Cyan

try {
    aws ec2 describe-key-pairs --key-names $KEY_PAIR_NAME --region $AWS_REGION >$null 2>&1
    Write-Host "✅ Key pair $KEY_PAIR_NAME already exists" -ForegroundColor Green
} catch {
    Write-Host "🔑 Creating key pair..." -ForegroundColor Cyan
    aws ec2 create-key-pair `
        --key-name $KEY_PAIR_NAME `
        --query 'KeyMaterial' `
        --output text `
        --region $AWS_REGION | Out-File -FilePath "$KEY_PAIR_NAME.pem" -Encoding ASCII
    Write-Host "✅ Key pair created: $KEY_PAIR_NAME.pem" -ForegroundColor Green
}

# Create user data script
Write-Host "📝 Creating user data script..." -ForegroundColor Cyan

$userData = @"
#!/bin/bash
yum update -y
yum install -y docker git

# Start Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-`$(uname -s)-`$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create app directory
mkdir -p /app
cd /app

# Create docker-compose.yml
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
    image: kasparro-etl:latest
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

# Note: You'll need to upload your Docker image or build it here
echo "Docker setup completed. Image needs to be uploaded."

# Set up cron for ETL (runs every hour)
echo "0 * * * * cd /app && /usr/local/bin/docker-compose exec -T app python -m ingestion.main >> /app/logs/etl-cron.log 2>&1" | crontab -
"@

$userData | Out-File -FilePath "user-data.sh" -Encoding UTF8

# Launch EC2 instance
Write-Host "🖥️ Launching EC2 instance..." -ForegroundColor Cyan

$INSTANCE_ID = aws ec2 run-instances `
    --image-id $AMI_ID `
    --count 1 `
    --instance-type $INSTANCE_TYPE `
    --key-name $KEY_PAIR_NAME `
    --security-group-ids $SECURITY_GROUP_ID `
    --user-data file://user-data.sh `
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=Kasparro-ETL-Server}]' `
    --query 'Instances[0].InstanceId' `
    --output text `
    --region $AWS_REGION

Write-Host "⏳ Waiting for instance to be running..." -ForegroundColor Cyan
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $AWS_REGION

# Get public IP
$PUBLIC_IP = aws ec2 describe-instances `
    --instance-ids $INSTANCE_ID `
    --query 'Reservations[0].Instances[0].PublicIpAddress' `
    --output text `
    --region $AWS_REGION

# Clean up
Remove-Item "user-data.sh" -Force

Write-Host ""
Write-Host "🎉 AWS Deployment Completed!" -ForegroundColor Green
Write-Host "============================" -ForegroundColor Green
Write-Host "Instance ID: $INSTANCE_ID" -ForegroundColor Yellow
Write-Host "Public IP: $PUBLIC_IP" -ForegroundColor Yellow
Write-Host "Region: $AWS_REGION" -ForegroundColor Yellow
Write-Host ""
Write-Host "🔑 SSH Access:" -ForegroundColor Cyan
Write-Host "   ssh -i $KEY_PAIR_NAME.pem ec2-user@$PUBLIC_IP" -ForegroundColor White
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Wait 5-10 minutes for the server to fully initialize" -ForegroundColor White
Write-Host "2. SSH into the server and upload your Docker image" -ForegroundColor White
Write-Host "3. Start the application: docker-compose up -d" -ForegroundColor White
Write-Host "4. Test endpoints:" -ForegroundColor White
Write-Host "   • http://$PUBLIC_IP/health" -ForegroundColor White
Write-Host "   • http://$PUBLIC_IP/data" -ForegroundColor White
Write-Host "   • http://$PUBLIC_IP/stats" -ForegroundColor White
Write-Host ""
Write-Host "💡 To terminate when done:" -ForegroundColor Yellow
Write-Host "   aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $AWS_REGION" -ForegroundColor White
Write-Host ""
Write-Host "🔑 Key file saved as: $KEY_PAIR_NAME.pem" -ForegroundColor Green