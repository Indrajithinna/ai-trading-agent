# 🔴 Live Trading Guide

> ⚠️ **WARNING**: Live trading involves real money. Use at your own risk. Ensure thorough paper trading validation before proceeding.

---

## Prerequisites

Before going live, you MUST have:

- [ ] ✅ Paper traded for ≥ 2 weeks with consistent profits
- [ ] ✅ Win rate ≥ 60% in paper trading
- [ ] ✅ Profit factor ≥ 1.3
- [ ] ✅ Backtest results validated across 5+ years
- [ ] ✅ Flattrade API keys configured and tested
- [ ] ✅ Telegram alerts working and monitored
- [ ] ✅ Understood all risk limits and comfortable with capital allocation

---

## Step 1 — Configure Flattrade API

Ensure `.env` has valid Flattrade credentials:

```env
EXECUTION_MODE=live

FLATTRADE_API_KEY=your_real_api_key
FLATTRADE_API_SECRET=your_real_api_secret
FLATTRADE_TOTP_KEY=your_real_totp_key
FLATTRADE_CLIENT_ID=your_real_client_id
```

### Flattrade Account Requirements

1. **Active Trading Account** with Flattrade
2. **API Access** enabled (contact Flattrade support if needed)
3. **Sufficient margin** — minimum ₹8,000 recommended
4. **TOTP Authentication** set up for API sessions

---

## Step 2 — Understand the Live Execution Flow

```
Live Mode Differences vs Paper Trading:

┌──────────────────────────┬────────────────────┬────────────────────┐
│ Feature                  │ Paper Trading      │ Live Trading       │
├──────────────────────────┼────────────────────┼────────────────────┤
│ Data Source              │ Simulated          │ Flattrade WebSocket│
│ Order Execution          │ Simulated          │ Real API orders    │
│ Slippage                 │ 0-0.2% simulated   │ Real market impact │
│ Balance                  │ Virtual ₹8,000     │ Real account funds │
│ Risk                     │ None               │ Real money at risk │
│ Square-off               │ Virtual close      │ Real position exit │
│ Telegram Alerts          │ Same               │ Same               │
└──────────────────────────┴────────────────────┴────────────────────┘
```

---

## Step 3 — Risk Management for Live Trading

### Capital Allocation

| Parameter | Recommended Start | After 1 Month | After 3 Months |
|-----------|------------------|---------------|----------------|
| Capital | ₹8,000 | ₹15,000 | ₹25,000+ |
| Max Daily Loss | ₹400 (5%) | ₹600 (4%) | ₹800 (3.2%) |
| Risk per Trade | 1% | 1.5% | 2% |
| Max Trades/Day | 5 | 8 | 10 |

### Safety Rules

1. **Start small** — Begin with minimum capital (₹8,000)
2. **Scale gradually** — Increase capital only after 1 month of consistent profits
3. **Monitor daily** — Check the dashboard and Telegram alerts throughout market hours
4. **Kill switch** — Be ready to stop the system immediately if something goes wrong
5. **Never override risk limits** — If the system stops trading, trust it

---

## Step 4 — Start Live Trading

```bash
# Ensure EXECUTION_MODE=live in .env
python -m ai_trading_agent.main --mode trade
```

### First-Day Checklist

- [ ] Run before market open (before 9:15 AM IST)
- [ ] Verify "Flattrade authentication successful" log
- [ ] Confirm Telegram "System Started" notification received
- [ ] Watch first trade signal carefully
- [ ] Monitor P&L throughout the day
- [ ] Verify square-off at 3:20 PM
- [ ] Review daily summary at 3:30 PM

---

## Step 5 — Monitoring

### Real-Time Monitoring

```bash
# Terminal 1: Trading system
python -m ai_trading_agent.main --mode trade

# Terminal 2: Dashboard
python -m ai_trading_agent.main --mode dashboard
```

### Key Alerts to Watch

| Alert | Action |
|-------|--------|
| 🚫 "Trading STOPPED: Daily loss limit" | System working correctly — no action |
| 🚫 "Trading STOPPED: Max trades reached" | System working correctly — no action |
| ❌ "Authentication failed" | Check API keys; system falls back to simulation |
| 🚨 "SYSTEM ALERT: error" | Investigate immediately |
| 🛑 Multiple consecutive SL hits | Consider pausing and reviewing strategy |

---

## Step 6 — Daily Routine

```
 8:45 AM  │ Start the system, verify authentication
 9:00 AM  │ Pre-market preparation runs automatically
 9:15 AM  │ Market opens — streaming begins
 9:30 AM  │ ORB period complete — trading starts
          │ Monitor trades via Telegram + Dashboard
 3:20 PM  │ Auto square-off of all positions
 3:30 PM  │ Daily summary sent — review performance
 3:45 PM  │ Stop system gracefully (Ctrl+C)
 4:00 PM  │ Review logs and data/performance_*.json
```

---

## Emergency Procedures

### Stop the System Immediately

```bash
# Press Ctrl+C in the terminal running the agent
# This triggers graceful shutdown:
# 1. All positions squared off
# 2. State saved to disk
# 3. Telegram "System Stopped" notification sent
```

### Manual Position Close

If the system crashes with open positions:

1. Log in to Flattrade web/mobile app
2. Manually close all open positions
3. Verify with your order book

### Disable Trading Temporarily

Set in `.env`:
```env
EXECUTION_MODE=paper
```

Then restart the system — it will run in paper mode only.

---

## Post-Live Validation

After 1 week of live trading:

| Metric | Paper Trading | Live Trading | Status |
|--------|--------------|-------------|--------|
| Win Rate | __%  | __% | Should be within 10% |
| Profit Factor | __.__ | __.__ | Should be > 1.0 |
| Avg Slippage | 0.1% | __% | Should be < 0.5% |
| Max Drawdown | ₹____ | ₹____ | Should be within limits |
| Execution Filled | 100% | __% | Should be > 95% |

If live results are significantly worse than paper:
1. Reduce position sizes
2. Increase min_trade_score to 80
3. Increase min_ai_probability to 0.80
4. Run more paper trading tests before retrying
