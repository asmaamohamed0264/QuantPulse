# QuantPulse - Deployment Guide

## VPS Deployment with Dokploy

### Prerequisites
- VPS with Docker and Dokploy installed
- Domain name pointed to your VPS
- SSL certificate (Let's Encrypt recommended)

### Environment Variables Setup

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Update the following critical values:
- `SECRET_KEY`: Generate a strong secret key
- `DATABASE_URL`: PostgreSQL connection string
- `ALPACA_API_KEY` & `ALPACA_SECRET_KEY`: Your Alpaca trading credentials
- `STRIPE_*` variables: Stripe payment integration keys
- `ALLOWED_IPS`: Comma-separated list of allowed IPs

### Database Setup

1. Create PostgreSQL database:
```sql
CREATE DATABASE quantpulse;
CREATE USER quantpulse WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE quantpulse TO quantpulse;
```

2. Run migrations:
```bash
just init-db
```

### Docker Deployment

#### Option 1: Dokploy Dashboard
1. Login to your Dokploy dashboard
2. Create new project "QuantPulse"
3. Add application from Git repository
4. Set environment variables in Dokploy UI
5. Configure domains and SSL
6. Deploy

#### Option 2: Manual Docker
```bash
# Build the image
just build

# Run with Docker Compose
docker-compose up -d
```

### Post-Deployment Setup

1. **Create Subscription Plans**:
Access the admin panel and create the default subscription plans:
- QuantPulse Basic: $29/month
- QuantPulse Plus: $79/month  
- QuantPulse Ultra: $199/month

2. **Setup Stripe Webhooks**:
Configure webhook endpoint: `https://quantpulse.qub3.uk/api/v1/stripe/webhook`

3. **Test Webhook Endpoint**:
```bash
curl -X POST https://quantpulse.qub3.uk/api/v1/webhook/test-strategy-uuid \
  -H "Content-Type: application/json" \
  -d '{"action": "buy", "symbol": "BTCUSD", "test_mode": true}'
```

### Monitoring & Logs

- Application logs: `docker-compose logs -f app`
- Health check: `https://quantpulse.qub3.uk/health`
- API documentation: `https://quantpulse.qub3.uk/docs` (if DEBUG=true)

### Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Setup proper ALLOWED_IPS whitelist
- [ ] Enable SSL/HTTPS
- [ ] Configure firewall rules
- [ ] Set DEBUG=false in production
- [ ] Setup database backups
- [ ] Monitor webhook request logs

### Scaling Considerations

For high-volume usage:
1. Setup Redis for caching
2. Configure Celery for background tasks
3. Use load balancer for multiple instances
4. Setup database read replicas
5. Implement rate limiting at nginx level

### Backup Strategy

1. **Database backups**:
```bash
pg_dump quantpulse > backup_$(date +%Y%m%d).sql
```

2. **Environment variables backup**:
Store `.env` file securely (encrypted)

3. **Application logs**:
Setup log rotation and archival

### Troubleshooting

Common issues:
- **Database connection**: Check DATABASE_URL format
- **Alpaca API**: Verify API credentials and paper trading settings
- **Webhooks failing**: Check IP whitelist and payload format
- **Memory issues**: Increase Docker memory limits

### Support

For deployment assistance:
- Check logs: `just logs`
- Health check: `curl http://localhost:8000/health`
- Database status: `just db-status` (if implemented)

## TradingView Integration

### Webhook URL Format
```
https://quantpulse.qub3.uk/api/v1/webhook/{strategy-uuid}
```

### Example TradingView Alert Script
```javascript
{
  "action": "{{strategy.order.action}}",
  "symbol": "{{ticker}}",
  "price": {{close}},
  "strategy": "{{strategy.order.id}}",
  "test_mode": false
}
```

### Security Notes
- Each strategy has unique UUID
- IP whitelist protects webhook endpoints
- Rate limiting prevents abuse
- All requests are logged for audit