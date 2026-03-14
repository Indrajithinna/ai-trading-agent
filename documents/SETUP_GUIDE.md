# 🛠️ Setup Guide

Complete step-by-step guide to get the AI Trading Agent Platform running on your machine.

---

## Prerequisites

| Requirement | Minimum Version | Purpose |
|-------------|----------------|---------|
| **Python** | 3.10+ | Core runtime |
| **pip** | 23.0+ | Package manager |
| **Git** | 2.30+ | Version control |
| **Windows / Linux / macOS** | Any | OS support |
| **Internet** | Required | For yfinance data downloads, Telegram, Flattrade API |

---

## Step 1 — Clone the Repository

```bash
git clone <repository-url>
cd ai_trading_agent
```

---

## Step 2 — Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

---

## Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Required Packages

| Package | Purpose |
|---------|---------|
| `pandas` | Data manipulation |
| `numpy` | Numerical computation |
| `requests` | HTTP API calls |
| `scikit-learn` | ML models (RandomForest) |
| `yfinance` | Historical market data for backtesting |
| `matplotlib` | Chart generation |
| `streamlit` | Dashboard UI |
| `websocket-client` | Real-time data streaming |
| `pytz` | Timezone handling (IST) |
| `python-dotenv` | Environment variable loading |

### Optional Packages

```bash
# XGBoost (if ML models need it)
pip install xgboost

# TA-Lib (alternative technical analysis — requires C library)
pip install ta-lib
```

---

## Step 4 — Configure Environment Variables

```bash
# Copy the example .env file
cp .env.example .env
```

Then edit `.env` with your credentials:

```env
# Execution Mode: "paper" (default) or "live"
EXECUTION_MODE=paper

# ─── Flattrade API ───────────────────────────────
FLATTRADE_API_KEY=your_api_key_here
FLATTRADE_API_SECRET=your_api_secret_here
FLATTRADE_TOTP_KEY=your_totp_key_here
FLATTRADE_CLIENT_ID=your_client_id_here

# ─── Telegram Bot ────────────────────────────────
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### How to Get Flattrade API Keys

1. Log in to [Flattrade PI Connect](https://piconnect.flattrade.in)
2. Navigate to **API Keys** → Generate API Key + Secret
3. Enable TOTP authentication and note your TOTP Key
4. Your Client ID is your Flattrade Login ID

### How to Set Up Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow instructions → get **Bot Token**
3. Create/open a channel or group → add the bot as admin
4. Get **Chat ID**: send a message, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates`

---

## Step 5 — Verify Installation

```bash
# Run the demo mode (no API keys needed)
python -m ai_trading_agent.main --mode demo
```

You should see output like:

```
══════════════════════════════════════════════════════════
🤖 AUTONOMOUS AI TRADING AGENT PLATFORM
📅 Date: 07-Mar-2026
💰 Capital: ₹8,000.00
📄 Mode: PAPER
══════════════════════════════════════════════════════════
🔄 Initializing all modules...
✅ All 19 modules initialized successfully!
🎭 Running demo trading cycle...
...
✅ Demo complete! System is ready for paper trading.
```

---

## Step 6 — Directory Structure After Setup

```
ai_trading_agent/
├── .env                  ← Your environment variables (git-ignored)
├── .env.example          ← Template
├── data/                 ← Auto-created runtime data
├── logs/                 ← Auto-created log files
├── models/saved/         ← Auto-created ML model checkpoints
└── ...
```

---

## Troubleshooting

### ❌ `ModuleNotFoundError: No module named 'ai_trading_agent'`

Run from the parent directory:
```bash
cd d:\Trading       # parent of ai_trading_agent/
python -m ai_trading_agent.main --mode demo
```

### ❌ `yfinance download returns empty DataFrame`

- Check internet connection
- Yahoo Finance may be temporarily unavailable
- Try with a different symbol: `--symbol NIFTY`

### ❌ `Flattrade authentication failed`

- The system gracefully falls back to simulation mode
- Verify API keys in `.env`
- Check if Flattrade services are operational

### ❌ `Telegram messages not sending`

- Ensure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set
- Verify the bot has admin access to the chat/channel
- The system will log "[Telegram Disabled]" if credentials are missing (this is fine for testing)

---

## Next Steps

| What to do | Guide |
|------------|-------|
| Run a backtest | [BACKTESTING_GUIDE.md](BACKTESTING_GUIDE.md) |
| Start paper trading | [PAPER_TRADING_GUIDE.md](PAPER_TRADING_GUIDE.md) |
| Go live | [LIVE_TRADING_GUIDE.md](LIVE_TRADING_GUIDE.md) |
| Deploy to server | [DEPLOYMENT.md](DEPLOYMENT.md) |
