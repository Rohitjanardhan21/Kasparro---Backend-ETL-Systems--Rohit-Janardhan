# Security Guidelines

## Environment Variables

This project uses environment variables for all sensitive configuration:

### Required Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@host:port/database

# API Keys (Optional - system works without them)
COINGECKO_API_KEY=your_coingecko_api_key_here
COINPAPRIKA_API_KEY=your_coinpaprika_api_key_here

# Database Password (for Docker deployments)
POSTGRES_PASSWORD=your_secure_database_password
```

### Security Best Practices

1. **Never commit secrets to version control**
2. **Use environment variables for all sensitive data**
3. **Use different credentials for different environments**
4. **Rotate API keys regularly**
5. **Use strong, unique passwords**

### Local Development

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
# Edit .env with your actual values
```

### Production Deployment

Set environment variables in your deployment platform:

- **AWS**: Use AWS Secrets Manager or environment variables
- **Render**: Set in dashboard environment variables
- **Railway**: Use railway CLI or dashboard
- **Docker**: Use docker-compose environment files

## API Key Management

### CoinGecko API
- Free tier: No key required (10-50 calls/minute)
- Paid tier: Set COINGECKO_API_KEY environment variable

### CoinPaprika API  
- Free tier: No key required (unlimited requests)
- Pro tier: Set COINPAPRIKA_API_KEY environment variable

## Database Security

- Use strong passwords
- Enable SSL/TLS connections in production
- Restrict database access to application servers only
- Regular security updates and patches