# QuantPulse - Automated Trading Service

QuantPulse is a professional automated trading service that executes trades based on TradingView webhook signals, similar to Tickerly but self-hosted on VPS with Dokploy.

## Features

- 🔒 Secure webhook endpoints for TradingView signals
- 🏦 Multi-broker support (starting with Alpaca)
- 📊 Multiple subscription plans with usage limits
- 🔐 IP whitelist & UUID authentication
- 📈 Real-time trade execution and monitoring
- 💳 Stripe payment integration
- 🎯 Test mode for simulations
- 📱 Web dashboard for management

## Subscription Plans

### QuantPulse Basic
- Crypto trading only
- 5 active strategies
- 100 alerts/day
- $29/month

### QuantPulse Plus
- Crypto + Forex + Stocks
- 15 active strategies
- 500 alerts/day
- $79/month

### QuantPulse Ultra
- All markets + MT4/MT5 support
- Unlimited strategies
- Unlimited alerts
- Prop firm integration
- $199/month

**30-day free trial available for all plans**

## Quick Start

```bash
# Build and run with Docker
just build
just run

# Or manually
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Architecture

- **Backend**: Python 3.12+ with FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT + IP whitelist
- **Payments**: Stripe integration
- **Deployment**: Docker + Dokploy
- **Monitoring**: Built-in logging and metrics

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.