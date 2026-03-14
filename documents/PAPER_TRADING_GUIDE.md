# 📄 Paper Trading Guide

How to use the AI Trading Agent in **Paper Trading** mode — simulating live market execution without risking real capital.

---

## What is Paper Trading?

Paper trading is a **simulated trading environment** where:

- ✅ All strategy signals are generated from real or simulated data
- ✅ Orders are "executed" with realistic slippage simulation
- ✅ Balance, P&L, positions, and risk are tracked like real trading
- ✅ Telegram alerts are sent (if configured)
- ❌ No real money is at risk
- ❌ No actual orders are placed with the broker

---

## Quick Start

```bash
# Start paper trading (works during market hours or falls back to demo)
python -m ai_trading_agent.main --mode trade
```

If the market is closed, it automatically runs a demo cycle.

---

## How It Works

### Market Hours Workflow (9:15 AM – 3:30 PM IST)

```
 9:00 AM  │ Pre-market — AI model training on recent data
 9:15 AM  │ Market opens — data streaming begins
 9:30 AM  │ ORB period complete — opening range established
 9:30 AM+ │ Trading ticks — full 15-step pipeline on each tick
 3:20 PM  │ Square-off — all open positions closed
 3:30 PM  │ Daily summary — performance report sent via Telegram
```

### What Happens on Each Tick

1. Feature Engineering computes 30+ indicators
2. 3 strategies evaluate independently in parallel
3. AI model predicts direction + probability
4. RL agent provides its recommendation
5. Signal aggregator checks consensus (≥3/4 agents agree)
6. Trade score engine assigns a composite score (0–100)
7. Risk manager validates (capital, daily limits, trade count)
8. Paper trader simulates execution with slippage
9. Telegram alert sent
10. Performance recorded

---

## Paper Trader Features

### Order Simulation

| Feature | Details |
|---------|---------|
| **Slippage** | Random 0–0.2% added to entry price |
| **Position Sizing** | 1–2% of capital risk per trade |
| **SL/TP Monitoring** | Automatic exit when stop-loss or target is hit |
| **Max Trades** | 10 per day |
| **Square-off** | All positions closed at 3:20 PM IST |

### Risk Controls

| Control | Limit |
|---------|-------|
| Initial Capital | ₹8,000 |
| Max Daily Loss | ₹400 |
| Daily Profit Target | ₹600 |
| Max Trades/Day | 10 |
| Risk per Trade | 1–2% of capital |
| Max 50% capital per single trade |

When any limit is hit, trading stops for the day.

---

## Configuration

All paper trading parameters are in `config.py`:

```python
class TradingConfig:
    initial_capital: float = 8000.0
    max_daily_loss: float = 400.0
    daily_profit_target: float = 600.0
    max_trades_per_day: int = 10
    risk_per_trade_min: float = 0.01   # 1%
    risk_per_trade_max: float = 0.02   # 2%
    min_trade_score: float = 70.0
    min_ai_probability: float = 0.70
    min_consensus_agents: int = 3
```

Ensure `.env` has:
```env
EXECUTION_MODE=paper
```

---

## Monitoring Paper Trades

### Via Telegram

If configured, you'll receive:

- 🟢/🔴 **Trade Signals** with entry, targets, SL, score, AI confidence
- 🎯/🛑 **Trade Updates** when targets or SL are hit
- 📋 **Daily Summary** at 3:30 PM with all stats

### Via Dashboard

```bash
python -m ai_trading_agent.main --mode dashboard
```

The Streamlit dashboard shows:
- Real-time portfolio status
- Open positions with unrealised P&L
- Trade history
- Risk status
- Performance metrics

### Via Console Logs

All activity is logged to `logs/trading_agent.log`:
```
2026-03-07 10:15:32 | MainOrchestrator | INFO | 🎉 TRADE EXECUTED: NIFTY 24300 CE | Score: 83
2026-03-07 10:45:18 | PaperTrader | INFO | 💚 Position Closed | NIFTY 24300 CE | P&L: ₹45.00 | Reason: TARGET_HIT
```

---

## State Persistence

Paper trading state is saved automatically:

| File | Contents |
|------|----------|
| `data/paper_trading_state.json` | Balance, stats, closed trades |
| `data/performance_YYYY-MM-DD.json` | Daily performance report |
| `models/saved/rl_agent.pkl` | RL agent checkpoint |

State is restored when you restart the system.

---

## Tips for Paper Trading

1. **Run for at least 2 weeks** before considering live trading
2. **Monitor win rate** — target ≥ 60% before going live
3. **Check profit factor** — should be consistently > 1.3
4. **Watch max drawdown** — if it exceeds ₹400/day, parameters need tuning
5. **Compare with backtest** — paper results should be within 20% of backtest
6. **Review Telegram signals** — manually verify the logic makes sense

---

## Transitioning to Live Trading

When paper trading results are consistently profitable:

1. Run for ≥ 2 full weeks with positive P&L
2. Achieve win rate ≥ 60%
3. Profit factor ≥ 1.3
4. Max drawdown within acceptable limits

Then proceed to [LIVE_TRADING_GUIDE.md](LIVE_TRADING_GUIDE.md).
