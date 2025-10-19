# 🚀 Alpaca Webhook Trader - Configurat pentru Paper Trading

## ✅ Status Configurare:
- **Fork-ul este gata**: https://github.com/asmaamohamed0264/webhook-trader
- **Acreditarile Alpaca sunt configurate** pentru paper trading
- **Baza de date PostgreSQL** este configurată în Dokploy
- **Environment variables** sunt pregătite

## 🔑 Acreditarile Tale (deja configurate):
- **API Key**: `PKGU5Z2MR2QF6CZN3KSHLW3T6Z`
- **Secret Key**: `9XS54h71XE74Tny73Wqg5PgNZ6rn9YVi`
- **Paper Trading**: Activ (TEST_MODE=True)
- **Bot Name**: `alpaca-paper-bot`

## 📋 Următorii Pași:

### 1. Push Modificările pe GitHub
```bash
git add .
git commit -m "Configure Alpaca credentials for paper trading"
git push origin main
```

### 2. Configurează în Dokploy
În Dokploy, configurează repository-ul ca:
- **Repository**: `asmaamohamed0264/webhook-trader`
- **Branch**: `main`
- **Build Path**: `/`

### 3. Environment Variables în Dokploy
Adaugă aceste variabile în Dokploy:
```
ALPACA_API_KEYS=PKGU5Z2MR2QF6CZN3KSHLW3T6Z
ALPACA_API_SECRETS=9XS54h71XE74Tny73Wqg5PgNZ6rn9YVi
ALPACA_NAMES=alpaca-paper-bot
ALPACA_PAPER=1
IP_WHITELIST=127.0.0.1,localhost
DB_URI=postgresql://webhook_user:webhook_secure_pass_2024@webhook-trader-db:5432/webhook_trader
DB_ECHO=True
TEST_MODE=True
```

### 4. Deploy Aplicația
1. Configurează build type: `Dockerfile`
2. Configurează portul: `8000`
3. Deploy aplicația

## 🧪 Testare:
După deploy, testează webhook-ul:
```bash
curl -X POST "https://your-app-url.com/webhook/alpaca-paper-bot" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "buy",
    "ticker": "AAPL",
    "quantity": 1,
    "price": 150.00
  }'
```

## 📞 Suport:
- **Repository tău**: https://github.com/asmaamohamed0264/webhook-trader
- **Repository original**: https://github.com/chand1012/webhook-trader
- **Documentație Alpaca**: https://alpaca.markets/docs/

---
**Notă**: Aplicația este configurată pentru paper trading. Pentru trading real, schimbă TEST_MODE=False și folosește acreditarile live de la Alpaca.
