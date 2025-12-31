@echo off
echo 🚀 AWS Deployment for Kasparro ETL System
echo ==========================================

REM Set AWS CLI path
set AWS_CLI="C:\Program Files\Amazon\AWSCLIV2\aws.exe"
if not exist %AWS_CLI% (
    set AWS_CLI="D:\aws.exe"
)
if not exist %AWS_CLI% (
    echo ❌ AWS CLI not found. Please check installation.
    pause
    exit /b 1
)

echo ✅ Using AWS CLI at: %AWS_CLI%

REM Test AWS CLI
%AWS_CLI% --version
if %errorlevel% neq 0 (
    echo ❌ AWS CLI not working properly
    pause
    exit /b 1
)

echo ✅ AWS CLI is working

REM Test AWS credentials
%AWS_CLI% sts get-caller-identity >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ AWS credentials not configured
    echo Please run: %AWS_CLI% configure
    echo.
    echo You need:
    echo - AWS Access Key ID
    echo - AWS Secret Access Key
    echo - Default region: us-east-1
    echo - Default output format: json
    pause
    exit /b 1
)

echo ✅ AWS credentials configured

REM Set variables
set AWS_REGION=us-east-1
set INSTANCE_TYPE=t3.medium
set KEY_PAIR_NAME=kasparro-key

echo 📦 Getting latest Amazon Linux AMI...

REM Get latest Amazon Linux AMI
for /f "tokens=*" %%i in ('%AWS_CLI% ec2 describe-images --owners amazon --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" --query "Images | sort_by(@, &CreationDate) | [-1].ImageId" --output text --region %AWS_REGION%') do set AMI_ID=%%i

echo 📦 Using AMI: %AMI_ID%

echo 🔒 Creating security group...

REM Create security group (ignore error if exists)
%AWS_CLI% ec2 create-security-group --group-name kasparro-etl-sg --description "Security group for Kasparro ETL" --region %AWS_REGION% >nul 2>&1

REM Get security group ID
for /f "tokens=*" %%i in ('%AWS_CLI% ec2 describe-security-groups --group-names kasparro-etl-sg --query "SecurityGroups[0].GroupId" --output text --region %AWS_REGION%') do set SECURITY_GROUP_ID=%%i

echo 🔒 Security group: %SECURITY_GROUP_ID%

echo 🔓 Adding security group rules...

REM Add security group rules (ignore errors if rules exist)
%AWS_CLI% ec2 authorize-security-group-ingress --group-id %SECURITY_GROUP_ID% --protocol tcp --port 22 --cidr 0.0.0.0/0 --region %AWS_REGION% >nul 2>&1
%AWS_CLI% ec2 authorize-security-group-ingress --group-id %SECURITY_GROUP_ID% --protocol tcp --port 80 --cidr 0.0.0.0/0 --region %AWS_REGION% >nul 2>&1
%AWS_CLI% ec2 authorize-security-group-ingress --group-id %SECURITY_GROUP_ID% --protocol tcp --port 8080 --cidr 0.0.0.0/0 --region %AWS_REGION% >nul 2>&1

echo 🔑 Checking key pair...

REM Check if key pair exists
%AWS_CLI% ec2 describe-key-pairs --key-names %KEY_PAIR_NAME% --region %AWS_REGION% >nul 2>&1
if %errorlevel% neq 0 (
    echo 🔑 Creating key pair...
    %AWS_CLI% ec2 create-key-pair --key-name %KEY_PAIR_NAME% --query "KeyMaterial" --output text --region %AWS_REGION% > %KEY_PAIR_NAME%.pem
    echo ✅ Key pair created: %KEY_PAIR_NAME%.pem
) else (
    echo ✅ Key pair %KEY_PAIR_NAME% already exists
)

echo 📝 Creating user data script...

REM Create user data script
(
echo #!/bin/bash
echo yum update -y
echo yum install -y docker git
echo systemctl start docker
echo systemctl enable docker
echo usermod -a -G docker ec2-user
echo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s^)-$(uname -m^)" -o /usr/local/bin/docker-compose
echo chmod +x /usr/local/bin/docker-compose
echo mkdir -p /app
echo cd /app
echo # Create docker-compose.yml
echo cat ^> docker-compose.yml ^<^< 'COMPOSE_EOF'
echo version: '3.8'
echo services:
echo   db:
echo     image: postgres:15
echo     environment:
echo       POSTGRES_DB: kasparro_etl
echo       POSTGRES_USER: postgres
echo       POSTGRES_PASSWORD: \${POSTGRES_PASSWORD:-secure_db_password}
echo     volumes:
echo       - postgres_data:/var/lib/postgresql/data
echo     healthcheck:
echo       test: ["CMD-SHELL", "pg_isready -U postgres"]
echo       interval: 10s
echo       timeout: 5s
echo       retries: 5
echo     restart: unless-stopped
echo   app:
echo     image: kasparro-etl:latest
echo     ports:
echo       - "80:8000"
echo       - "8080:8000"
echo     environment:
echo       - DATABASE_URL=postgresql://postgres:\${POSTGRES_PASSWORD:-secure_db_password}@db:5432/kasparro_etl
echo       - COINGECKO_API_KEY=\${COINGECKO_API_KEY}
echo       - COINPAPRIKA_API_KEY=
echo       - ENVIRONMENT=production
echo       - LOG_LEVEL=INFO
echo     depends_on:
echo       db:
echo         condition: service_healthy
echo     volumes:
echo       - ./data:/app/data
echo       - ./logs:/app/logs
echo     restart: unless-stopped
echo     healthcheck:
echo       test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
echo       interval: 30s
echo       timeout: 10s
echo       retries: 3
echo volumes:
echo   postgres_data:
echo COMPOSE_EOF
echo mkdir -p data logs
echo # Set up cron for ETL
echo echo "0 * * * * cd /app && /usr/local/bin/docker-compose exec -T app python -m ingestion.main >> /app/logs/etl-cron.log 2>&1" ^| crontab -
echo echo "Server setup completed. Docker image needs to be uploaded."
) > user-data.sh

echo 🖥️ Launching EC2 instance...

REM Launch EC2 instance
for /f "tokens=*" %%i in ('%AWS_CLI% ec2 run-instances --image-id %AMI_ID% --count 1 --instance-type %INSTANCE_TYPE% --key-name %KEY_PAIR_NAME% --security-group-ids %SECURITY_GROUP_ID% --user-data file://user-data.sh --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=Kasparro-ETL-Server}]" --query "Instances[0].InstanceId" --output text --region %AWS_REGION%') do set INSTANCE_ID=%%i

echo ⏳ Waiting for instance to be running...
%AWS_CLI% ec2 wait instance-running --instance-ids %INSTANCE_ID% --region %AWS_REGION%

REM Get public IP
for /f "tokens=*" %%i in ('%AWS_CLI% ec2 describe-instances --instance-ids %INSTANCE_ID% --query "Reservations[0].Instances[0].PublicIpAddress" --output text --region %AWS_REGION%') do set PUBLIC_IP=%%i

REM Clean up
del user-data.sh

echo.
echo 🎉 AWS EC2 Instance Created Successfully!
echo ========================================
echo Instance ID: %INSTANCE_ID%
echo Public IP: %PUBLIC_IP%
echo Region: %AWS_REGION%
echo SSH Key: %KEY_PAIR_NAME%.pem
echo.
echo 🔑 SSH Access:
echo    ssh -i %KEY_PAIR_NAME%.pem ec2-user@%PUBLIC_IP%
echo.
echo 📋 Next Steps:
echo 1. Wait 5 minutes for server initialization
echo 2. SSH into the server
echo 3. Upload your Docker image or build it:
echo    docker build -t kasparro-etl:latest .
echo 4. Start the application:
echo    docker-compose up -d
echo 5. Test your API:
echo    http://%PUBLIC_IP%/health
echo    http://%PUBLIC_IP%/data
echo    http://%PUBLIC_IP%/stats
echo.
echo 💡 To terminate when done:
echo    %AWS_CLI% ec2 terminate-instances --instance-ids %INSTANCE_ID% --region %AWS_REGION%
echo.

pause