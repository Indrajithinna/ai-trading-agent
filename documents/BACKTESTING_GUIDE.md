# 📉 Backtesting Guide

How to backtest the AI Trading Agent's strategies against 5–10 years of real historical market data.

---

## Overview

The backtesting engine:

1. **Downloads real OHLCV data** from Yahoo Finance for NIFTY (`^NSEI`), BANKNIFTY (`^NSEBANK`), and SENSEX (`^BSESN`)
2. **Walks forward bar-by-bar** through the entire history
3. **Runs all 3 strategies** (VWAP, EMA, ORB) on each bar
4. **Tracks trades** with stop-loss, take-profit, and max-hold period exits
5. **Generates analytics** — both a JSON report and an interactive HTML dashboard

---

## Quick Start

```bash
# Default: 5 years, all symbols, ₹1,00,000 capital
python -m ai_trading_agent.main --mode backtest
```

---

## Command Reference

```bash
python -m ai_trading_agent.main --mode backtest [OPTIONS]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--years` | int | 5 | Years of historical data (1–10) |
| `--symbol` | str | All markets | Comma-separated: `NIFTY`, `BANKNIFTY`, `SENSEX` |
| `--capital` | float | 100000 | Initial capital in ₹ |

### Examples

```bash
# 10 years, NIFTY only
python -m ai_trading_agent.main --mode backtest --years 10 --symbol NIFTY

# 7 years, NIFTY + BANKNIFTY, ₹50K capital
python -m ai_trading_agent.main --mode backtest --years 7 --symbol NIFTY,BANKNIFTY --capital 50000

# Full 10-year backtest across all markets
python -m ai_trading_agent.main --mode backtest --years 10
```

---

## What Happens During a Backtest

### Step 1 — Data Download

The engine downloads daily OHLCV data from Yahoo Finance:

| Symbol | Yahoo Ticker | Typical Data Range |
|--------|-------------|-------------------|
| NIFTY | `^NSEI` | 2016–2026 (10 years) |
| BANKNIFTY | `^NSEBANK` | 2016–2026 |
| SENSEX | `^BSESN` | 2016–2026 |

### Step 2 — Bar-by-Bar Walk-Forward

For each bar (starting from bar 100 for indicator warm-up):

1. **Feature Engineering**: Compute RSI, MACD, EMA, VWAP, ATR, ADX, Bollinger, etc.
2. **Strategy Evaluation**: Run VWAP, EMA, and ORB strategies
3. **Signal Filtering**: Only accept signals with confidence ≥ 30%
4. **Position Management**: Track SL/TP on open positions
5. **Equity Tracking**: Snapshot equity after each bar

### Step 3 — Trade Exits

Trades exit via one of:

| Exit Reason | Description |
|-------------|-------------|
| `TARGET1` | Price hit Target 1 |
| `TARGET2` | Price hit Target 2 |
| `STOPLOSS` | Price hit stop-loss |
| `MAX_HOLD` | Held for 5 bars (max holding period) |
| `BACKTEST_END` | Forced close at end of data |

### Step 4 — Report Generation

Two output files are generated and saved to `data/`:

- **`backtest_report.json`** — Machine-readable results with all trades
- **`backtest_report.html`** — Interactive HTML analytics dashboard

---

## Output Analytics

### Console Summary

```
═══════════════════════════════════════════════════════════
  📊  BACKTEST RESULTS
═══════════════════════════════════════════════════════════
  Period          : last 5 years
  Symbols         : NIFTY, BANKNIFTY, SENSEX
  Initial Capital : ₹1,00,000
  Final Capital   : ₹1,12,345
  Total Return    : +12.35%
──────────────────────────────────────────────────────────
  Total Trades    : 1,247
  Win / Loss      : 723 / 524
  Win Rate        : 57.98%
  Net P&L         : ₹12,345.00
  Profit Factor   : 1.43
  ...
```

### HTML Report Features

The interactive HTML report (`backtest_report.html`) includes:

| Section | Contents |
|---------|----------|
| **KPI Cards** | Total return, Net P&L, Win rate, Profit factor, Sharpe, Sortino, Max DD |
| **Equity Curve** | Line chart of capital over time |
| **Yearly P&L** | Bar chart showing annual performance |
| **Strategy Breakdown** | Grouped bar chart — P&L and win rate per strategy |
| **Exit Reasons** | Doughnut chart — proportion of SL/TP/MAX_HOLD exits |
| **Monthly Heatmap** | Colour-coded table of monthly P&L by year |
| **Trade Log** | Scrollable table with all 200 most recent trades |

---

## Interpreting Results

### Key Metrics to Watch

| Metric | Good | Concerning |
|--------|------|-----------|
| **Win Rate** | > 55% | < 45% |
| **Profit Factor** | > 1.5 | < 1.0 |
| **Sharpe Ratio** | > 1.0 | < 0.5 |
| **Max Drawdown** | < 15% of capital | > 25% |
| **Expectancy** | Positive | Negative |
| **Avg Win : Avg Loss** | > 1.2:1 | < 0.8:1 |

### Strategy Comparison

Compare each strategy's performance to identify:

- Which strategy works best in the current market regime
- Which produces the most false signals
- Risk-reward ratio per strategy

---

## Customisation

### Modify Strategy Parameters

Edit `config.py` to tune before backtesting:

```python
class StrategyConfig:
    vwap_rsi_buy_threshold: float = 60.0    # Try 55, 65
    vwap_rsi_sell_threshold: float = 40.0   # Try 35, 45
    ema_fast_period: int = 9                # Try 5, 7, 12
    ema_slow_period: int = 21               # Try 15, 25, 30
    orb_breakout_buffer: float = 0.1        # Try 0.05, 0.15, 0.2
```

### Modify Backtest Parameters

In `execution/backtester.py`:

```python
class BacktestEngine:
    LOOKBACK = 100          # Bars before first signal
    MAX_DAILY_TRADES = 10   # Per-day trade cap
    MAX_OPEN_POSITIONS = 3  # Concurrent positions
```

---

## Limitations

1. **Daily bars only** — Yahoo Finance free tier provides daily OHLCV; intraday (1m/5m) data is limited to ~60 days
2. **No options pricing** — Backtest runs on underlying index data, not actual option premiums
3. **No slippage model** — The current backtest uses direct price execution
4. **No brokerage/commission** — Transaction costs are not deducted
5. **Survivorship bias** — Only tests on current major indices

These limitations mean backtest results are **optimistic** compared to real-world performance. Always discount results by 20–30%.
