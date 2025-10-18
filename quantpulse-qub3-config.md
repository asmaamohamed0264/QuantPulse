# QuantPulse - Configurare pentru quantpulse.qub3.uk

## 🌐 Domain Configuration

**Primary Domain**: `quantpulse.qub3.uk`

## 🚀 Dokploy Deployment Steps

### 1. Domain Configuration in Dokploy UI

În dashboard-ul Dokploy, pentru aplicația QuantPulse:

```
Domain Settings:
- Domain: quantpulse.qub3.uk
- Path: /
- Port: 8000
- HTTPS: Enabled (Let's Encrypt)
- Redirect HTTP to HTTPS: Yes
```

### 2. Environment Variables for Production

```bash
# App Configuration
APP_NAME=QuantPulse
DEBUG=false
VERSION=1.0.0
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-super-secret-key-quantpulse-2024
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database Configuration  
DATABASE_URL=postgresql://quantpulse:quantpulse_secure_2024@quantpulse-db:5432/quantpulse

# CORS Configuration for Production
CORS_ORIGINS=https://quantpulse.qub3.uk

# Alpaca Trading API
ALPACA_API_KEY=your-alpaca-api-key
ALPACA_SECRET_KEY=your-alpaca-secret-key
ALPACA_PAPER=true
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Stripe Payment Integration
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_key
STRIPE_SECRET_KEY=sk_live_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Security & Rate Limiting
ALLOWED_IPS=127.0.0.1,::1,52.89.214.238,34.212.75.30,54.218.53.128,52.32.178.7
WEBHOOK_RATE_LIMIT=1000

# Logging
LOG_FILE=/app/logs/quantpulse.log
```

### 3. DNS Configuration Required

Asigură-te că DNS record-ul pentru `quantpulse.qub3.uk` pointează la serverul tău Dokploy:

```dns
Type: A
Name: quantpulse
Value: YOUR_DOKPLOY_SERVER_IP
TTL: 300 (5 minutes)
```

### 4. SSL Certificate

Dokploy va genera automat certificatul Let's Encrypt pentru `quantpulse.qub3.uk`.

### 5. Post-Deployment Verification

#### Health Check
```bash
curl https://quantpulse.qub3.uk/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "QuantPulse", 
  "version": "1.0.0"
}
```

#### API Documentation
- **OpenAPI Docs**: `https://quantpulse.qub3.uk/docs` (dacă DEBUG=true)
- **ReDoc**: `https://quantpulse.qub3.uk/redoc` (dacă DEBUG=true)

#### Webhook Test
```bash
curl -X POST https://quantpulse.qub3.uk/api/v1/webhook/test-strategy-uuid \
  -H "Content-Type: application/json" \
  -d '{
    "action": "buy",
    "symbol": "BTCUSD",
    "test_mode": true
  }'
```

## 🔐 Security Configuration for Production

### TradingView IP Whitelist
```bash
# TradingView webhook IPs (add to ALLOWED_IPS)
52.89.214.238,34.212.75.30,54.218.53.128,52.32.178.7
```

### Rate Limiting
- **Production**: 1000 requests/hour per user
- **Development**: 100 requests/hour per user

### HTTPS Enforcement
- All HTTP traffic redirected to HTTPS
- HSTS headers enabled
- Secure cookies only

## 📊 Monitoring & Analytics

### Key Metrics to Monitor
- **Webhook latency**: < 200ms average
- **Database connections**: < 80% pool usage
- **Error rate**: < 1% of total requests
- **SSL certificate expiry**: Auto-renewal 30 days before

### Log Locations
- **Application logs**: Dokploy UI → QuantPulse → View Logs
- **Database logs**: PostgreSQL container logs
- **Nginx logs**: Reverse proxy access/error logs

## 🎯 TradingView Integration

### Webhook URL Format
```
https://quantpulse.qub3.uk/api/v1/webhook/{strategy-uuid}
```

### Example Alert Message for TradingView
```json
{
  "action": "{{strategy.order.action}}",
  "symbol": "{{ticker}}",
  "price": {{close}},
  "quantity": {{strategy.position_size}},
  "strategy": "{{strategy.order.id}}",
  "test_mode": false,
  "timestamp": "{{time}}"
}
```

## 🚀 Go-Live Checklist

- [ ] DNS propagated for quantpulse.qub3.uk
- [ ] SSL certificate active
- [ ] Database connection working
- [ ] Alpaca API credentials configured
- [ ] TradingView IPs whitelisted
- [ ] Health check responding
- [ ] Webhook test successful
- [ ] Monitoring configured
- [ ] Backup strategy in place

## 📞 Support Endpoints

- **Health**: `https://quantpulse.qub3.uk/health`
- **API Status**: `https://quantpulse.qub3.uk/api/v1/status` (if implemented)
- **Version**: Available in health check response

**QuantPulse will be live at: https://quantpulse.qub3.uk 🚀**