# Alternative Cloud Deployment (Without AWS CLI)

Since AWS CLI setup is having issues, here are alternative ways to deploy your Kasparro ETL system:

## Option 1: Manual AWS Console Deployment

### Step 1: Launch EC2 Instance via AWS Console
1. Go to https://console.aws.amazon.com/ec2/
2. Click "Launch Instance"
3. Choose "Amazon Linux 2 AMI"
4. Instance type: t3.medium (or t2.micro for free tier)
5. Create new key pair: "kasparro-key" (download the .pem file)
6. Security group: Allow SSH (22), HTTP (80), and Custom TCP (8080)
7. Launch instance

### Step 2: Connect to Your Instance
1. Note your instance's public IP from the EC2 console
2. Use PuTTY or Windows Terminal to SSH:
   ```
   ssh -i kasparro-key.pem ec2-user@YOUR_PUBLIC_IP
   ```

### Step 3: Set Up Docker on the Server
```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker git
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in for Docker permissions
exit
```

### Step 4: Upload Your Docker Image
```bash
# SSH back in
ssh -i kasparro-key.pem ec2-user@YOUR_PUBLIC_IP

# Create app director