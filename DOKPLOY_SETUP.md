# QuantPulse - Deployment în Dokploy UI

## Pasul 1: Accesare Dokploy Dashboard

1. Conectează-te la dashboard-ul Dokploy: `https://your-server-ip:3000`
2. Login cu credentialele admin

## Pasul 2: Creare Proiect

1. Click pe **"New Project"**
2. **Project Name**: `QuantPulse`
3. **Description**: `Professional Automated Trading Service for TradingView Webhooks`
4. Click **"Create Project"**

## Pasul 3: Creare Bază de Date PostgreSQL

1. În proiectul QuantPulse, click pe **"Add Service" → "Database" → "PostgreSQL"**
2. Configurări:
   - **Service Name**: `quantpulse-db`
   - **Database Name**: `quantpulse`
   - **Database User**: `quantpulse`
   - **Database Password**: `quantpulse_secure_2024` (schimbă cu o parolă sigură)
   - **Docker Image**: `postgres:15-alpine`
   - **Port**: `5432` (default)
3. **Environment Variables**:
   ```
   POSTGRES_DB=quantpulse
   POSTGRES_USER=quantpulse
   POSTGRES_PASSWORD=quantpulse_secure_2024
   ```
4. Click **"Create Database"**

## Pasul 4: Creare Aplicație QuantPulse

1. Click pe **"Add Service" → "Application"**
2. **Source Type**: Selectează **"Git Repository"**
3. Repository Settings:
   - **Repository URL**: URL-ul repository-ului tău QuantPulse
   - **Branch**: `main` sau `master`
   - **Build Path**: `/` (root)
4. **Application Name**: `quantpulse-app`
5. **Port**: `8000`

## Pasul 5: Configurare Environment Variables

În secțiunea **"Environment Variables"** pentru aplicație, adaugă:

```bash
# App Configuration
APP_NAME=QuantPulse
DEBUG=false
VERSION=1.0.0
LOG_LEVEL=INFO

# Security (IMPORTANT: Generează keys puternice!)
SECRET_KEY=your-super-secret-key-change-this-now
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database Configuration
DATABASE_URL=postgresql://quantpulse:quantpulse_secure_2024@quantpulse-db:5432/quantpulse

# Redis (optional, dacă adaugi Redis later)
REDIS_URL=redis://redis:6379

# Alpaca Trading API (Adaugă credentialele tale)
ALPACA_API_KEY=your-alpaca-api-key
ALPACA_SECRET_KEY=your-alpaca-secret-key
ALPACA_PAPER=true
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Stripe Payment Integration (Pentru producție)
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_key
STRIPE_SECRET_KEY=sk_test_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Security & Rate Limiting
ALLOWED_IPS=127.0.0.1,::1
WEBHOOK_RATE_LIMIT=100

# Logging
LOG_FILE=/app/logs/quantpulse.log
```

## Pasul 6: Configurare Build Settings

1. **Build Command**: `pip install -r requirements.txt`
2. **Start Command**: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
3. **Dockerfile**: Utilizar el Dockerfile din repository

## Pasul 7: Configurare Domeniu și SSL

1. În secțiunea **"Domains"**:
   - **Domain**: `quantpulse.qub3.uk`
   - **Enable SSL**: Activează (Let's Encrypt)
   - **Path**: `/`
   - **Port**: `8000`
2. Click **"Add Domain"**

## Pasul 8: Deploy Aplicația

1. Click pe **"Deploy"** pentru aplicația QuantPulse
2. Monitorizează logs-urile pentru erori
3. După deploy, verifică health check: `https://quantpulse.qub3.uk/health`

## Pasul 9: Verificare Post-Deploy

### Test Webhook Endpoint
```bash
curl -X POST https://quantpulse.qub3.uk/api/v1/webhook/test-strategy-uuid \
  -H "Content-Type: application/json" \
  -d '{
    "action": "buy",
    "symbol": "BTCUSD", 
    "test_mode": true
  }'
```

### Check API Documentation
- Dacă DEBUG=true: `https://quantpulse.qub3.uk/docs`
- Health check: `https://quantpulse.qub3.uk/health`

## Pasul 10: Configurări de Producție

### Database Migrations
După primul deploy, execută:
```bash
# În containerul aplicației
python -c "from app.database import create_tables; create_tables()"
```

### Monitorizare
- Logs aplicație: Dokploy → QuantPulse → View Logs
- Database monitoring: Verifică conexiunea PostgreSQL
- SSL certificate: Auto-renewal Let's Encrypt

## Pasul 11: Configurare TradingView

1. **Webhook URL Format**: 
   ```
   https://quantpulse.qub3.uk/api/v1/webhook/{strategy-uuid}
   ```

2. **TradingView Alert Script**:
   ```json
   {
     "action": "{{strategy.order.action}}",
     "symbol": "{{ticker}}",
     "price": {{close}},
     "quantity": 0.001,
     "test_mode": false
   }
   ```

## Troubleshooting

### Probleme Comune:

1. **Database Connection Error**:
   - Verifică că PostgreSQL service rulează
   - Confirmă DATABASE_URL este corect
   - Testează conexiunea din aplicație

2. **Webhook Errors**:
   - Verifică IP whitelist în ALLOWED_IPS
   - Confirmă payload format în TradingView
   - Check logs pentru debugging

3. **SSL Issues**:
   - Verifică că domeniul pointează la server
   - Așteaptă propagarea DNS
   - Re-issue certificatul Let's Encrypt

### Comenzi Utile:

```bash
# View application logs
docker logs quantpulse-app-container-name

# Check database connectivity
docker exec -it quantpulse-db-container psql -U quantpulse -d quantpulse

# Restart application
# Folosește Dokploy UI pentru restart
```

## Securitate în Producție

- [ ] Schimbă toate parolele din .env.example
- [ ] Configurează ALLOWED_IPS cu IP-urile TradingView
- [ ] Setează DEBUG=false
- [ ] Activează SSL/HTTPS
- [ ] Setup database backups
- [ ] Monitorizează webhook logs

**QuantPulse va fi gata să proceseze webhook-uri TradingView după configurarea completă! 🚀**