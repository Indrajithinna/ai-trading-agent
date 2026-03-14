# 🏗️ System Architecture

## Overview

The AI Trading Agent Platform follows a **multi-agent, event-driven architecture** where specialised modules handle distinct responsibilities and communicate through a central orchestrator.

---

## High-Level Architecture

```
                         ┌────────────────────────┐
                         │   TradingOrchestrator   │
                         │      (main.py)          │
                         └──────────┬─────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
    ┌─────▼─────┐           ┌──────▼──────┐           ┌──────▼──────┐
    │  DATA     │           │  ANALYSIS   │           │  EXECUTION  │
    │  LAYER    │           │  LAYER      │           │  LAYER      │
    └───────────┘           └─────────────┘           └─────────────┘
```

---

## Layer Breakdown

### 1. Data Layer

| Module | File | Responsibility |
|--------|------|---------------|
| **Market Data Agent** | `agents/market_data_agent.py` | Fetches real-time ticks via Flattrade WebSocket/REST; generates simulated data for paper/demo modes |
| **Feature Engineering** | `agents/feature_engineering_agent.py` | Computes 30+ technical indicators: RSI, MACD, EMA, VWAP, ATR, ADX, Bollinger Bands, OBV, Stochastic, candlestick patterns |

### 2. Analysis Layer

| Module | File | Responsibility |
|--------|------|---------------|
| **Market Scanner** | `agents/scanner_agent.py` | Scans for momentum, volume spikes, breakouts, and reversals |
| **Regime Detector** | `agents/regime_detector.py` | Classifies market as TRENDING, SIDEWAYS, or VOLATILE using ADX + ATR |
| **Multi-Timeframe Engine** | `agents/multi_timeframe_engine.py` | Ensures 15m (trend), 5m (setup), 1m (entry) alignment before trading |
| **VWAP Strategy** | `strategies/vwap_strategy.py` | Price > VWAP + RSI > 60 + Volume spike → BUY CALL |
| **EMA Strategy** | `strategies/ema_strategy.py` | EMA9 crosses above EMA21 + MACD confirmation → BUY CALL |
| **ORB Strategy** | `strategies/orb_strategy.py` | Price breaks first 15-min candle high/low → BUY CALL/PUT |
| **AI Prediction Model** | `models/ai_prediction_model.py` | RandomForest + XGBoost ensemble; predicts BUY_CALL/BUY_PUT/HOLD with probability |
| **RL Agent** | `models/reinforcement_learning_agent.py` | Deep Q-Network with experience replay; learns optimal action policy |
| **Signal Aggregator** | `agents/signal_aggregator.py` | Consensus rule: ≥3 agents agree → allow trade |
| **Trade Score Engine** | `agents/signal_aggregator.py` | Weighted composite score (0–100) from trend, VWAP, RSI, volume, AI, RL, regime, MTF |
| **Strike Selector** | `agents/signal_aggregator.py` | ATM for moderate, OTM for high, ITM for low confidence |

### 3. Execution Layer

| Module | File | Responsibility |
|--------|------|---------------|
| **Risk Manager** | `risk/risk_manager.py` | Enforces capital limits, daily loss/profit caps, trade count limits, position sizing |
| **Paper Trader** | `execution/paper_trader.py` | Simulated order execution with slippage, SL/TP monitoring, balance management |
| **Flattrade Executor** | `execution/flattrade_executor.py` | Live order placement via Flattrade API (for real trading) |
| **Performance Analyzer** | `execution/performance_analyzer.py` | Tracks win rate, P&L, Sharpe, Sortino, max drawdown, equity curve |
| **Backtesting Engine** | `execution/backtester.py` | Walk-forward backtest on 5–10 years of historical data |
| **Backtest Analytics** | `execution/backtest_analytics.py` | Interactive HTML report with Chart.js visualisations |

### 4. Support Layer

| Module | File | Responsibility |
|--------|------|---------------|
| **Telegram Alerts** | `signals/telegram_alert.py` | Sends real-time trade signals, updates, and daily summaries via Telegram Bot |
| **Market Scheduler** | `scheduler/market_scheduler.py` | IST-based event scheduler: pre-market, market open, ORB, trading ticks, square-off, daily summary |
| **Strategy Optimizer** | `optimizer/strategy_optimizer.py` | Auto-tunes strategy parameters using grid search, random search, or genetic algorithms |
| **Dashboard** | `dashboard/app.py` | Streamlit web UI: live portfolio, signals, risk, performance |
| **Configuration** | `config.py` | Centralised dataclass configuration with env var overrides |

---

## 15-Step Trading Pipeline

Every trading tick executes this pipeline:

```
 Step 1  │ Market Data Agent fetches latest OHLCV data
 Step 2  │ Feature Engineering computes 30+ technical indicators
 Step 3  │ Market Scanner identifies opportunities
 Step 4  │ Regime Detector classifies market (Trending/Sideways/Volatile)
 Step 5  │ Multi-Timeframe Engine checks 15m/5m/1m alignment
 Step 6  │ 3 Strategy Agents generate signals in parallel
 Step 7  │ AI Prediction Model gives direction + probability
 Step 8  │ RL Agent provides action recommendation
 Step 9  │ Signal Aggregator checks consensus (≥3 agents)
 Step 10 │ Trade Score Engine computes composite score (0–100)
 Step 11 │ Smart Strike Selector picks optimal strike
 Step 12 │ Risk Manager validates the trade (capital, limits)
 Step 13 │ Paper Trader executes the trade
 Step 14 │ Telegram sends alert to user
 Step 15 │ Performance Analyzer records the trade
```

---

## Data Flow Diagram

```
  Yahoo Finance / Flattrade API
            │
            ▼
  ┌─────────────────────┐
  │  Raw OHLCV Data     │
  │  (open, high, low,  │
  │   close, volume)    │
  └─────────┬───────────┘
            │
            ▼
  ┌─────────────────────┐       ┌──────────────────┐
  │  Feature Engineered │──────▶│  AI/ML Models    │
  │  DataFrame (30+     │       │  (RF, XGB, DQN)  │
  │  columns)           │       └────────┬─────────┘
  └─────────┬───────────┘                │
            │                            │
            ▼                            ▼
  ┌─────────────────────┐      ┌─────────────────┐
  │  Strategy Signals   │─────▶│  Aggregation &  │
  │  (VWAP, EMA, ORB)   │      │  Consensus      │
  └─────────────────────┘      └────────┬────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │  Trade Score +   │
                               │  Strike Selection│
                               └────────┬────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │  Risk Manager   │
                               │  (Allow/Deny)   │
                               └────────┬────────┘
                                        │
                             ┌──────────┼──────────┐
                             ▼                     ▼
                    ┌────────────────┐   ┌────────────────┐
                    │ Paper Trader   │   │ Telegram Alert  │
                    │ (Execute)      │   │ (Notify)        │
                    └────────────────┘   └────────────────┘
```

---

## Module Numbering

| # | Module | Status |
|---|--------|--------|
| 1 | Market Data Agent | ✅ Complete |
| 2 | Market Scanner | ✅ Complete |
| 3 | Feature Engineering | ✅ Complete |
| 4 | Regime Detector | ✅ Complete |
| 5 | Multi-Timeframe Engine | ✅ Complete |
| 6a | VWAP Breakout Strategy | ✅ Complete |
| 6b | EMA Momentum Strategy | ✅ Complete |
| 6c | ORB Strategy | ✅ Complete |
| 7 | AI Prediction Model | ✅ Complete |
| 8 | RL Trading Agent | ✅ Complete |
| 9 | Signal Aggregator | ✅ Complete |
| 10 | Trade Score Engine | ✅ Complete |
| 11 | Smart Strike Selector | ✅ Complete |
| 12 | Risk Manager | ✅ Complete |
| 13 | Telegram Alerts | ✅ Complete |
| 14 | Paper Trader | ✅ Complete |
| 15 | Performance Analyzer | ✅ Complete |
| 16 | Strategy Optimizer | ✅ Complete |
| 17 | Market Scheduler | ✅ Complete |
| 18 | Dashboard (Streamlit) | ✅ Complete |
| 19 | Flattrade Executor | ✅ Complete |
| 20 | Backtesting Engine | ✅ Complete |
| 21 | Backtest Analytics | ✅ Complete |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Data | pandas, numpy, yfinance |
| ML/AI | scikit-learn (RandomForest, XGBoost), custom DQN |
| Broker | Flattrade REST + WebSocket API |
| Notifications | Telegram Bot API |
| Dashboard | Streamlit |
| Visualisation | Chart.js (HTML reports), matplotlib |
| Scheduling | Custom IST-aware scheduler |
| Configuration | dataclasses + python-dotenv |
| Logging | Python logging (rotating file handler) |

---

## Design Principles

1. **Modularity** — Each module has a single responsibility with clean interfaces
2. **Fail-safe** — Simulation fallback when API credentials are missing
3. **Consensus-based** — No single strategy trades alone; ≥3 agents must agree
4. **Risk-first** — Multiple risk checks before any trade is allowed
5. **Extensible** — New strategies plug in by extending `BaseStrategy`
6. **Observable** — Every action is logged, alerted, and recorded for analysis
