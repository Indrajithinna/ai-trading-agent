# 📝 Changelog

All notable changes to the AI Trading Agent Platform.

---

## [1.1.0] — 2026-03-07

### Added
- **Backtesting Engine** (`execution/backtester.py`) — Walk-forward backtest over 5–10 years of real historical OHLCV data from Yahoo Finance
- **Backtest Analytics** (`execution/backtest_analytics.py`) — Self-contained HTML report with Chart.js visualisations (equity curve, yearly P&L, strategy breakdown, exit reasons, monthly heatmap, trade log)
- **`--mode backtest`** CLI flag with `--years`, `--symbol`, and `--capital` options
- **Complete documentation suite** in `documents/` folder:
  - `README.md` — Project overview and quick start
  - `ARCHITECTURE.md` — System design, pipelines, data flow
  - `SETUP_GUIDE.md` — Step-by-step installation and configuration
  - `BACKTESTING_GUIDE.md` — How to backtest with historical data
  - `PAPER_TRADING_GUIDE.md` — Paper trading setup and usage
  - `LIVE_TRADING_GUIDE.md` — Real trading with Flattrade API
  - `API_REFERENCE.md` — Module-by-module API documentation
  - `DEPLOYMENT.md` — Server, Docker, and cloud deployment
  - `FUTURE_SCOPE.md` — Roadmap and planned features
  - `CHANGELOG.md` — This file

### Changed
- Updated `requirements.txt` — Added `yfinance` and `matplotlib` dependencies
- Updated `main.py` — Added backtest mode integration with CLI arguments

---

## [1.0.0] — 2026-03-06

### Added — Initial Release
- **Module 1**: Market Data Agent — Flattrade API + WebSocket + simulation
- **Module 2**: Market Scanner — Momentum, volume, breakout, reversal scanning
- **Module 3**: Feature Engineering — 30+ technical indicators
- **Module 4**: Regime Detector — Trending / Sideways / Volatile classification
- **Module 5**: Multi-Timeframe Engine — 1m / 5m / 15m alignment
- **Module 6a**: VWAP Breakout Strategy
- **Module 6b**: EMA Momentum Strategy
- **Module 6c**: Opening Range Breakout Strategy
- **Module 7**: AI Prediction Model — RandomForest + XGBoost ensemble
- **Module 8**: RL Trading Agent — Deep Q-Network with experience replay
- **Module 9**: Signal Aggregator — Consensus-based (≥3/4 agents)
- **Module 10**: Trade Score Engine — Composite score (0–100)
- **Module 11**: Smart Strike Selector — ATM / OTM / ITM selection
- **Module 12**: Risk Manager — Capital limits, daily loss/profit caps
- **Module 13**: Telegram Alert System — Trade signals, updates, daily summaries
- **Module 14**: Paper Trading Engine — Simulated execution with slippage
- **Module 15**: Performance Analyzer — P&L, Sharpe, Sortino, drawdown
- **Module 16**: Strategy Optimizer — Grid search, random search, genetic algorithm
- **Module 17**: Market Scheduler — IST-aware event scheduling
- **Module 18**: Streamlit Dashboard — Real-time web UI
- **Module 19**: Flattrade Executor — Live order placement
- **Central Orchestrator** — 15-step trading pipeline
- **Configuration system** — Dataclass-based with environment variable overrides
- **Logging** — Rotating file handler + console logging
