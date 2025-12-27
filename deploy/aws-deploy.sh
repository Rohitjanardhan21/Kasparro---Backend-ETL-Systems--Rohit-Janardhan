#!/bin/bash

# AWS Deployment Script for Kasparro ETL System
# This script deploys the system to AWS using EC2 and RDS

set -e

echo "🚀 Starting AWS deployment for Kasparro ETL System..."

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
KEY_PAIR_NAME=${KEY_PAIR_NAME:-kasparro-etl-key}
SECURITY_GROUP_NAME=${SECURITY_GROUP_NAME:-kasparro-etl-sg}
INSTANCE_TYPE=${INSTANCE_TYPE:-t3.medium}
RDS_INSTANCE_CLASS=${RDS_INSTANCE_CLASS:-db.t3.micro}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install it first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Build and push Docker image to ECR
echo "📦 Building and pushing Docker image..."

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/kasparro-etl"

# Create ECR repository if it doesn't exist
aws ecr describe-repositories --repository-names kasparro-etl --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository --repository-name kasparro-etl --region $AWS_REGION

# Get login token and login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI

# Build and tag image
docker build -t kasparro-etl:latest .
docker tag kasparro-etl:latest $ECR_REPOSITORY_URI:latest

# Push image
docker push $ECR_REPOSITORY_URI:latest

echo "✅ Docker image pushed to ECR: $ECR_REPOSITORY_URI:latest"

# Create RDS instance
echo "🗄️ Creating RDS PostgreSQL instance..."

DB_INSTANCE_IDENTIFIER="kasparro-etl-db"
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Create RDS subnet group
aws rds create-db-subnet-group \
    --db-subnet-group-name kasparro-etl-subnet-group \
    --db-subnet-group-description "Subnet group for Kasparro ETL RDS" \
    --subnet-ids $(aws ec2 describe-subnets --query 'Subnets[0:2].SubnetId' --output text) \
    --region $AWS_REGION 2>/dev/null || echo "Subnet group already exists"

# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
    --db-instance-class $RDS_INSTANCE_CLASS \
    --engine postgres \
    --engine-version 15.4 \
    --master-username postgres \
    --master-user-password $DB_PASSWORD \
    --allocated-storage 20 \
    --db-name kasparro_etl \
    --vpc-security-group-ids $(aws ec2 describe-security-groups --group-names default --query 'SecurityGroups[0].GroupId' --output text) \
    --db-subnet-group-name kasparro-etl-subnet-group \
    --backup-retention-period 7 \
    --storage-encrypted \
    --region $AWS_REGION 2>/dev/null || echo "RDS instance already exists"

echo "⏳ Waiting for RDS instance to be available..."
aws rds wait db-instance-available --db-instance-identifier $DB_INSTANCE_IDENTIFIER --region $AWS_REGION

# Get RDS endpoint
RDS_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_IDENTIFIER --query 'DBInstances[0].Endpoint.Address' --output text --region $AWS_REGION)

echo "✅ RDS instance created: $RDS_ENDPOINT"

# Create security group
echo "🔒 Creating security group..."

SECURITY_GROUP_ID=$(aws ec2 create-security-group \
    --group-name $SECURITY_GROUP_NAME \
    --description "Security group for Kasparro ETL System" \
    --query 'GroupId' \
    --output text \
    --region $AWS_REGION 2>/dev/null || \
    aws ec2 describe-security-groups --group-names $SECURITY_GROUP_NAME --query 'SecurityGroups[0].GroupId' --output text --region $AWS_REGION)

# Add security group rules
aws ec2 authorize-security-group-ingress \
    --group-id $SECURITY_GROUP_ID \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "SSH rule already exists"

aws ec2 authorize-security-group-ingress \
    --group-id $SECURITY_GROUP_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "HTTP rule already exists"

aws ec2 authorize-security-group-ingress \
    --group-id $SECURITY_GROUP_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "API rule already exists"

echo "✅ Security group created: $SECURITY_GROUP_ID"

# Create key pair if it doesn't exist
if ! aws ec2 describe-key-pairs --key-names $KEY_PAIR_NAME --region $AWS_REGION &>/dev/null; then
    echo "🔑 Creating key pair..."
    aws ec2 create-key-pair --key-name $KEY_PAIR_NAME --query 'KeyMaterial' --output text --region $AWS_REGION > ${KEY_PAIR_NAME}.pem
    chmod 400 ${KEY_PAIR_NAME}.pem
    echo "✅ Key pair created: ${KEY_PAIR_NAME}.pem"
else
    echo "✅ Key pair already exists: $KEY_PAIR_NAME"
fi

# Create user data script
cat > user-data.sh << EOF
#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Create application directory
mkdir -p /app
cd /app

# Create environment file
cat > .env << EOL
DATABASE_URL=postgresql://postgres:$DB_PASSWORD@$RDS_ENDPOINT:5432/kasparro_etl
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
  app:
    image: $ECR_REPOSITORY_URI:latest
    ports:
      - "80:8000"
    env_file:
      - .env
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

# Login to ECR and start the application
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI
docker-compose up -d

# Setup cron for ETL
echo "0 * * * * cd /app && docker-compose exec -T app python -m ingestion.main >> /app/logs/etl-cron.log 2>&1" | crontab -
EOF

# Launch EC2 instance
echo "🖥️ Launching EC2 instance..."

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id ami-0abcdef1234567890 \
    --count 1 \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_PAIR_NAME \
    --security-group-ids $SECURITY_GROUP_ID \
    --user-data file://user-data.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=Kasparro-ETL-Server}]' \
    --iam-instance-profile Name=EC2-ECR-Role \
    --query 'Instances[0].InstanceId' \
    --output text \
    --region $AWS_REGION)

echo "⏳ Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $AWS_REGION

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region $AWS_REGION)

echo "✅ EC2 instance launched: $INSTANCE_ID"
echo "🌐 Public IP: $PUBLIC_IP"

# Create EventBridge rule for scheduled ETL
echo "⏰ Setting up scheduled ETL with EventBridge..."

# Create IAM role for EventBridge (if not exists)
aws iam create-role \
    --role-name EventBridge-ETL-Role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "events.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }' 2>/dev/null || echo "EventBridge role already exists"

# Create EventBridge rule
aws events put-rule \
    --name kasparro-etl-schedule \
    --schedule-expression "rate(1 hour)" \
    --description "Hourly ETL execution for Kasparro system" \
    --region $AWS_REGION

echo "✅ EventBridge rule created for hourly ETL execution"

# Clean up
rm -f user-data.sh

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Deployment Summary:"
echo "   • EC2 Instance ID: $INSTANCE_ID"
echo "   • Public IP: $PUBLIC_IP"
echo "   • RDS Endpoint: $RDS_ENDPOINT"
echo "   • ECR Repository: $ECR_REPOSITORY_URI"
echo "   • API URL: http://$PUBLIC_IP"
echo "   • Health Check: http://$PUBLIC_IP/health"
echo ""
echo "🔑 SSH Access:"
echo "   ssh -i ${KEY_PAIR_NAME}.pem ec2-user@$PUBLIC_IP"
echo ""
echo "📝 Next Steps:"
echo "   1. Set your API keys in the EC2 instance environment"
echo "   2. Test the API endpoints"
echo "   3. Monitor logs and metrics"
echo "   4. Set up CloudWatch alarms (optional)"
echo ""
echo "⚠️  Important: Save the database password: $DB_PASSWORD"