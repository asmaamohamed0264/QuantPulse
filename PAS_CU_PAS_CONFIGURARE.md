# 🚀 Ghid Pas cu Pas - Configurarea Alpaca Bot

## ✅ Status Actual
- **Proiect**: `alpaca_bot` - CREAT ✅
- **Baza de date PostgreSQL**: `webhook-trader-db` - RULEAZĂ ✅
- **Aplicația**: `webhook-trader` - CREAT ✅
- **Fork-ul GitHub**: `asmaamohamed0264/webhook-trader` - CREAT ✅
- **Acreditarile Alpaca**: CONFIGURATE ✅

## 📋 Pași pentru a face aplicația funcțională:

### PASUL 1: Accesează Dokploy Dashboard
1. Deschide browser-ul și mergi la dashboard-ul Dokploy
2. Navighează la proiectul **"alpaca_bot"**
3. Click pe aplicația **"webhook-trader"**

### PASUL 2: Configurează Repository-ul GitHub ✅ COMPLETAT
**✅ FORK-UL ESTE GATA**: Repository-ul tău este la https://github.com/asmaamohamed0264/webhook-trader

#### ✅ Ce am făcut automat:
- **Fork-ul a fost creat** cu succes
- **Acreditarile Alpaca** au fost configurate
- **Fișierul de configurare** `alpaca-config.env` a fost creat
- **Modificările** au fost push-ate pe GitHub

#### 2.1: Configurează în Dokploy
1. În aplicație, mergi la tab-ul **"Source"**
2. Configurează:
   - **Source Type**: `GitHub`
   - **Repository**: `asmaamohamed0264/webhook-trader`
   - **Branch**: `main`
   - **Build Path**: `/`
3. Salvează configurația

### PASUL 3: Configurează Build Type
1. Mergi la tab-ul **"Build"**
2. Setează:
   - **Build Type**: `Dockerfile`
   - **Docker Context Path**: `/`
   - **Dockerfile Path**: `Dockerfile` (sau lasă gol - va folosi Dockerfile-ul din repo)
3. Salvează configurația

**Notă**: Dockerfile-ul este în rădăcina repository-ului, deci calea este `Dockerfile`

### PASUL 4: Configurează Environment Variables
1. Mergi la tab-ul **"Environment"**
2. Adaugă următoarele variabile (una câte una):

```
ALPACA_API_KEYS=PKGU5Z2MR2QF6CZN3KSHLW3T6Z
```

```
ALPACA_API_SECRETS=9XS54h71XE74Tny73Wqg5PgNZ6rn9YVi
```

```
ALPACA_NAMES=alpaca-paper-bot
```

```
ALPACA_PAPER=1
```

```
IP_WHITELIST=127.0.0.1,localhost
```

```
DB_URI=postgresql://webhook_user:webhook_secure_pass_2024@webhook-trader-db:5432/webhook_trader
```

```
DB_ECHO=True
```

```
TEST_MODE=True
```

### PASUL 5: Configurează Portul
**Opțiunea 1 - Tab "Ports" (dacă există):**
1. Mergi la tab-ul **"Ports"**
2. Adaugă:
   - **Port**: `8000`
   - **Type**: `HTTP`
3. Salvează configurația

**Opțiunea 2 - Tab "Settings" sau "Configuration":**
1. Mergi la tab-ul **"Settings"** sau **"Configuration"**
2. Caută secțiunea **"Ports"** sau **"Network"**
3. Adaugă:
   - **Port**: `8000`
   - **Type**: `HTTP`

**Opțiunea 3 - Tab "Deploy" sau "Runtime":**
1. Mergi la tab-ul **"Deploy"** sau **"Runtime"**
2. Caută câmpul **"Port"** sau **"Exposed Port"**
3. Setează: `8000`

**Notă**: Portul 8000 este configurat în Dockerfile-ul aplicației, deci poate fi setat automat

### PASUL 6: Deploy Aplicația
1. Mergi la tab-ul **"Deployments"**
2. Click pe butonul **"Deploy"**
3. Așteaptă ca build-ul să se termine (poate dura 5-10 minute)

### PASUL 7: Testează Aplicația
1. După deploy, aplicația va avea un URL (ex: `https://app-program-back-end-pixel-wsjg6j.your-domain.com`)
2. Accesează URL-ul + `/docs` pentru a vedea API documentation
3. Testează webhook-ul cu un request POST

## 🧪 Testare Webhook

### Test cu curl:
```bash
curl -X POST "https://your-app-url.com/webhook/alpaca-paper-bot" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "buy",
    "symbol": "AAPL",
    "quantity": 1,
    "price": 150.00
  }'
```

### Test cu TradingView:
1. În TradingView, creează un alert
2. Setează webhook URL: `https://your-app-url.com/webhook/alpaca-paper-bot`
3. Configurează payload-ul JSON

## 📊 Monitorizare

### Logs:
- Mergi la tab-ul **"Logs"** în aplicație pentru a vedea log-urile
- Verifică dacă aplicația se conectează la baza de date
- Verifică dacă primește webhook-urile

### Database:
- Baza de date PostgreSQL rulează pe: `webhook-trader-db-ng6qts`
- Conectează-te cu: `webhook_user` / `webhook_secure_pass_2024`

## 🔧 Troubleshooting

### Dacă aplicația nu pornește:
1. Verifică log-urile pentru erori
2. Verifică dacă toate environment variables sunt setate corect
3. Verifică dacă baza de date rulează

### Dacă webhook-ul nu funcționează:
1. Verifică dacă IP-ul tău este în whitelist
2. Verifică formatul JSON al payload-ului
3. Verifică log-urile pentru erori de autentificare Alpaca

## 🎯 Următorii Pași

1. **Configurează TradingView alerts** pentru simbolurile dorite
2. **Testează cu tranzacții mici** în modul paper trading
3. **Monitorizează performanța** bot-ului
4. **Ajustează strategiile** bazat pe rezultate

## 📞 Suport

- **Repository tău (fork)**: https://github.com/asmaamohamed0264/webhook-trader
- **Repository original**: https://github.com/chand1012/webhook-trader
- **Documentație Alpaca**: https://alpaca.markets/docs/
- **TradingView Webhooks**: https://www.tradingview.com/support/solutions/43000529348

---

**Notă**: Aplicația este configurată pentru paper trading (TEST_MODE=True). Pentru trading real, schimbă TEST_MODE=False și folosește acreditarile live de la Alpaca.
