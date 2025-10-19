# Alpaca Bot - Webhook Trader Configuration Guide

## Project Created Successfully ✅

I've successfully created the "alpaca_bot" project in Dokploy with the following components:

### Project Details:
- **Project ID**: `er5JheNA12NmFp0Re3QG3`
- **Project Name**: `alpaca_bot`
- **Environment ID**: `VoX9ILi2d0uCaXQA-XMap`

### Components Created:

#### 1. PostgreSQL Database ✅
- **Database ID**: `uXwGHEbqYPTOe6-M4gTT9`
- **Name**: `webhook-trader-db`
- **App Name**: `webhook-trader-db-ng6qts`
- **Database Name**: `webhook_trader`
- **Username**: `webhook_user`
- **Password**: `webhook_secure_pass_2024`
- **Status**: Deployed and running

#### 2. Application ✅
- **Application ID**: `R956qc_3fs4KRyq-9daup`
- **Name**: `webhook-trader`
- **App Name**: `app-program-back-end-pixel-wsjg6j`
- **Status**: Created (needs configuration)

## Manual Configuration Steps

Due to some parameter formatting issues with the MCP server, you'll need to manually configure the application through the Dokploy web interface:

### 1. Configure GitHub Repository
1. Go to your Dokploy dashboard
2. Navigate to the "alpaca_bot" project
3. Click on the "webhook-trader" application
4. Go to "Source" tab
5. Configure:
   - **Source Type**: GitHub
   - **Repository**: `chand1012/webhook-trader`
   - **Branch**: `main`
   - **Build Path**: `/`

### 2. Configure Build Type
1. Go to "Build" tab
2. Set **Build Type**: `Dockerfile`
3. **Docker Context Path**: `/`
4. **Dockerfile**: Use the existing Dockerfile in the repository

### 3. Configure Environment Variables
Go to "Environment" tab and add these variables:

```env
# Alpaca API Configuration (YOUR REAL CREDENTIALS)
ALPACA_API_KEYS=PKGU5Z2MR2QF6CZN3KSHLW3T6Z
ALPACA_API_SECRETS=9XS54h71XE74Tny73Wqg5PgNZ6rn9YVi
ALPACA_NAMES=alpaca-paper-bot
ALPACA_PAPER=1

# IP Whitelist (Allow localhost and your IP)
IP_WHITELIST=127.0.0.1,localhost

# Database Configuration (Already configured)
DB_URI=postgresql://webhook_user:webhook_secure_pass_2024@webhook-trader-db:5432/webhook_trader
DB_ECHO=True

# Test Mode (Keep True for paper trading)
TEST_MODE=True
```

### 4. Configure Port
1. Go to "Ports" tab
2. Set **Port**: `8000`
3. Set **Type**: `HTTP`

### 5. Deploy the Application
1. Go to "Deployments" tab
2. Click "Deploy" to start the deployment

## Important Notes

### Security Configuration
- **Replace the Alpaca API keys** with your actual keys from your Alpaca account
- **Update the IP whitelist** with your actual IP addresses
- **Generate unique names** for your trading bots (use UUIDs for security)

### Database Connection
The PostgreSQL database is already configured and running. The connection string is:
```
postgresql://webhook_user:webhook_secure_pass_2024@webhook-trader-db:5432/webhook_trader
```

### TradingView Webhook Setup
Once deployed, you can configure TradingView webhooks to send signals to your application endpoint:
- **Webhook URL**: `https://your-domain.com/webhook/{bot-name}`
- **Method**: POST
- **Content-Type**: application/json

### Example TradingView Webhook Payload
```json
{
  "action": "buy",
  "symbol": "AAPL",
  "quantity": 10,
  "price": 150.00
}
```

## Next Steps

1. **Configure the application** using the steps above
2. **Deploy the application**
3. **Test the webhook endpoint**
4. **Configure TradingView alerts** to send webhooks to your application
5. **Monitor the application logs** for any issues

## Support

The webhook-trader application is based on the [chand1012/webhook-trader](https://github.com/chand1012/webhook-trader) repository. You can find more detailed documentation and examples in the repository.

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `ALPACA_API_KEYS` | Comma-separated Alpaca API keys | `PK1234567890,PK0987654321` |
| `ALPACA_API_SECRETS` | Comma-separated Alpaca API secrets | `SK1234567890,SK987654321` |
| `ALPACA_NAMES` | Comma-separated bot names | `trading-bot-1,trading-bot-2` |
| `ALPACA_PAPER` | Comma-separated paper trading flags | `1,0` (1=true, 0=false) |
| `IP_WHITELIST` | Comma-separated allowed IPs | `8.8.8.8,2001:4860:4860::8888` |
| `DB_URI` | Database connection string | `postgresql://user:pass@host:port/db` |
| `DB_ECHO` | Enable SQL logging | `True` |
| `TEST_MODE` | Test mode (no real trades) | `True` |

The project is now ready for configuration and deployment! 🚀
