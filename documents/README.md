<p align="center">
  <h1 align="center">🤖 Autonomous AI Trading Agent Platform</h1>
  <p align="center">
    A production-grade, multi-agent AI system for Indian options market analysis and automated trading.<br/>
    Supports <strong>Paper Trading</strong>, <strong>Backtesting</strong>, and <strong>Live Trading</strong> across NIFTY, BANKNIFTY & SENSEX.
  </p>
</p>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Run Modes](#run-modes)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Documentation](#documentation)
- [License](#license)

---

## Overview

The **AI Trading Agent Platform** is a fully autonomous trading system that combines:

- **3 Strategy Agents** (VWAP Breakout, EMA Momentum, Opening Range Breakout)
- **Machine Learning** (RandomForest + XGBoost ensemble classifier)
- **Reinforcement Learning** (DQN-based Q-learning agent)
- **Multi-Timeframe Analysis** (1m, 5m, 15m alignment)
- **Market Regime Detection** (Trending / Sideways / Volatile)
- **Risk Management** (per-trade risk, daily loss caps, max drawdown protection)
- **Smart Strike Selection** (ATM / OTM / ITM based on confidence)
- **Telegram Alerts** (real-time signals, updates, and daily summaries)
- **Backtesting Engine** (5–10 years of real historical data via Yahoo Finance)
- **Streamlit Dashboard** (real-time monitoring UI)

All modules are orchestrated by a central `TradingOrchestrator` that runs a 15-step pipeline on every market tick.

---

## Key Features

| Category | Feature | Details |
|----------|---------|---------|
| 📊 **Data** | Real-time + historical | Flattrade API (live) / yfinance (backtest) |
| 🧠 **AI/ML** | Ensemble + RL | RandomForest, XGBoost, Deep Q-Network |
| 📈 **Strategies** | VWAP, EMA, ORB | 3 independent strategy agents with consensus |
| 🔍 **Analysis** | 30+ indicators | RSI, MACD, Bollinger, ADX, VWAP, Stochastic, OBV… |
| 🛡️ **Risk** | Multi-layer | Daily loss limit, profit target, trade caps, position sizing |
| 📱 **Alerts** | Telegram Bot | Trade signals, updates, daily P&L summaries |
| 📉 **Backtest** | 5–10 years | Real OHLCV data, HTML analytics report |
| 🖥️ **Dashboard** | Streamlit | Live portfolio, signals, risk, performance |
| 🔧 **Optimizer** | Auto-tune | Grid search, random search, genetic algorithm |

---

## Architecture

```
┌─────────────────────────── ORCHESTRATOR ───────────────────────────┐
│                                                                     │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Market   │→ │ Feature   │→ │ Scanner  │→ │ Regime Detector  │  │
│  │ Data     │  │ Engineer  │  │ Agent    │  │ (Trend/Side/Vol) │  │
│  └──────────┘  └───────────┘  └──────────┘  └──────────────────┘  │
│        │                                           │                │
│        ▼                                           ▼                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              STRATEGY AGENTS (Parallel)                      │  │
│  │  ┌────────┐    ┌──────────┐    ┌──────────┐                 │  │
│  │  │  VWAP  │    │   EMA    │    │   ORB    │                 │  │
│  │  └────────┘    └──────────┘    └──────────┘                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
│        │                                                            │
│        ▼                                                            │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Signal   │→ │ Trade     │→ │ Strike   │→ │ Risk Manager     │  │
│  │ Aggreg.  │  │ Score     │  │ Selector │  │ (Limit Check)    │  │
│  └──────────┘  └───────────┘  └──────────┘  └──────────────────┘  │
│        │                                           │                │
│        ▼                                           ▼                │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ AI Model │  │ RL Agent  │  │  Paper   │  │ Performance      │  │
│  │ (ML)     │  │ (DQN)     │  │  Trader  │  │ Analyzer         │  │
│  └──────────┘  └───────────┘  └──────────┘  └──────────────────┘  │
│                                    │                                │
│                                    ▼                                │
│                    ┌──────────────────────────┐                     │
│                    │  Telegram Alerts  📱     │                     │
│                    │  Dashboard UI     🖥️     │                     │
│                    │  Backtest Report  📊     │                     │
│                    └──────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone <repository-url>
cd ai_trading_agent

# Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Flattrade API keys and Telegram bot token
```

### 3. Run

```bash
# Demo mode (simulated data, safe to run anytime)
python -m ai_trading_agent.main --mode demo

# Backtest mode (5 years of real historical data)
python -m ai_trading_agent.main --mode backtest --years 5

# Paper trading (live market hours, simulated execution)
python -m ai_trading_agent.main --mode trade

# Dashboard
python -m ai_trading_agent.main --mode dashboard
```

---

## Run Modes

| Mode | Command | Description |
|------|---------|-------------|
| **Demo** | `--mode demo` | One-cycle simulation using random data. Safe for testing. |
| **Backtest** | `--mode backtest` | Runs strategies on 5–10 years of real NIFTY/BANKNIFTY/SENSEX data. Generates HTML analytics. |
| **Trade** | `--mode trade` | Live paper trading during market hours (9:15 AM – 3:30 PM IST). |
| **Dashboard** | `--mode dashboard` | Launches Streamlit UI for real-time monitoring. |

### Backtest Options

```bash
python -m ai_trading_agent.main --mode backtest --years 10 --symbol NIFTY --capital 50000
```

| Flag | Default | Description |
|------|---------|-------------|
| `--years` | 5 | Years of historical data (1–10) |
| `--symbol` | All markets | Comma-separated symbols: `NIFTY,BANKNIFTY,SENSEX` |
| `--capital` | 100000 | Initial capital for the backtest |

---

## Project Structure

```
ai_trading_agent/
├── __init__.py                     # Package init
├── config.py                       # All configuration dataclasses
├── main.py                         # Entry point & TradingOrchestrator
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
│
├── agents/                         # Data & analysis agents
│   ├── market_data_agent.py        # Module 1  — Flattrade API + simulation
│   ├── scanner_agent.py            # Module 2  — Momentum/volume/breakout scanner
│   ├── feature_engineering_agent.py# Module 3  — 30+ technical indicators
│   ├── regime_detector.py          # Module 4  — Trending/Sideways/Volatile
│   ├── multi_timeframe_engine.py   # Module 5  — 1m/5m/15m alignment
│   └── signal_aggregator.py        # Modules 9/10/11 — Consensus + Score + Strike
│
├── strategies/                     # Strategy implementations
│   ├── base_strategy.py            # Abstract base class + SignalType enum
│   ├── vwap_strategy.py            # Module 6a — VWAP Breakout
│   ├── ema_strategy.py             # Module 6b — EMA Momentum
│   └── orb_strategy.py             # Module 6c — Opening Range Breakout
│
├── models/                         # ML / RL models
│   ├── ai_prediction_model.py      # Module 7  — RandomForest + XGBoost
│   └── reinforcement_learning_agent.py  # Module 8  — Deep Q-Network
│
├── risk/                           # Risk management
│   └── risk_manager.py             # Module 12 — Daily loss/profit/trade limits
│
├── signals/                        # Notifications
│   └── telegram_alert.py           # Module 13 — Telegram Bot alerts
│
├── execution/                      # Trade execution
│   ├── paper_trader.py             # Module 14 — Paper trading engine
│   ├── performance_analyzer.py     # Module 15 — P&L, Sharpe, drawdown
│   ├── flattrade_executor.py       # Module 19 — Live order execution (placeholder)
│   ├── backtester.py               # Backtesting engine (5–10 yr historical)
│   └── backtest_analytics.py       # HTML report generator
│
├── optimizer/                      # Strategy optimization
│   └── strategy_optimizer.py       # Module 16 — Grid/Random/Genetic search
│
├── scheduler/                      # Market timings
│   └── market_scheduler.py         # Module 17 — IST market event scheduler
│
├── dashboard/                      # Web UI
│   └── app.py                      # Module 18 — Streamlit dashboard
│
├── utils/                          # Shared utilities
│   ├── logger.py                   # Rotating file + console logger
│   └── helpers.py                  # IST helpers, formatting, signal IDs
│
├── data/                           # Runtime data (auto-generated)
│   ├── backtest_report.json        # Backtest results (JSON)
│   ├── backtest_report.html        # Backtest analytics (HTML)
│   ├── paper_trading_state.json    # Paper trading state
│   └── performance_*.json          # Daily performance reports
│
├── logs/                           # Log files (auto-generated)
│   └── trading_agent.log
│
└── documents/                      # Project documentation (this folder)
    ├── README.md
    ├── ARCHITECTURE.md
    ├── SETUP_GUIDE.md
    ├── BACKTESTING_GUIDE.md
    ├── PAPER_TRADING_GUIDE.md
    ├── LIVE_TRADING_GUIDE.md
    ├── API_REFERENCE.md
    ├── DEPLOYMENT.md
    └── FUTURE_SCOPE.md
```

---

## Configuration

All configuration is managed in `config.py` via dataclasses:

| Config Class | Key Parameters |
|---|---|
| `TradingConfig` | Capital (₹8K), daily loss (₹400), profit target (₹600), max 10 trades |
| `MarketConfig` | NIFTY, BANKNIFTY, SENSEX; 9:15–15:30 IST |
| `FlattradeConfig` | API key, secret, TOTP, client ID |
| `TelegramConfig` | Bot token, chat ID |
| `StrategyConfig` | RSI/MACD/EMA/ATR/ADX periods, VWAP thresholds |
| `AIModelConfig` | RF/XGB hyperparameters, feature list |
| `RLConfig` | Learning rate, gamma, epsilon, memory size |
| `OptimizerConfig` | Grid/random/genetic methods, population, generations |

Environment variables override defaults via `.env` file.

---

## Documentation

Detailed documentation is available in the [`documents/`](./documents/) folder:

| Document | Description |
|----------|-------------|
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Step-by-step installation & configuration |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, module interactions, data flow |
| [BACKTESTING_GUIDE.md](BACKTESTING_GUIDE.md) | How to backtest with 5–10 years of data |
| [PAPER_TRADING_GUIDE.md](PAPER_TRADING_GUIDE.md) | Paper trading setup & usage |
| [LIVE_TRADING_GUIDE.md](LIVE_TRADING_GUIDE.md) | Real trading with Flattrade API |
| [API_REFERENCE.md](API_REFERENCE.md) | Module-by-module API documentation |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Server deployment, Docker, cloud hosting |
| [FUTURE_SCOPE.md](FUTURE_SCOPE.md) | Roadmap & planned features |

---

## License

This project is proprietary software. All rights reserved.

---

<p align="center">
  Built with ❤️ by <strong>AI Trading Studio</strong>
</p>
