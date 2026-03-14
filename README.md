<p align="center">
  <h1 align="center">🤖 AI Trading Agent Platform</h1>
  <p align="center">
    <strong>Autonomous AI-powered trading system for Indian derivatives markets</strong>
  </p>
  <p align="center">
    <a href="#features">Features</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#strategies">Strategies</a> •
    <a href="#documentation">Documentation</a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT">
    <img src="https://img.shields.io/badge/broker-Flattrade-orange.svg" alt="Broker: Flattrade">
    <img src="https://img.shields.io/badge/market-NSE%20%7C%20BSE-red.svg" alt="Market: NSE | BSE">
    <img src="https://img.shields.io/badge/status-active-brightgreen.svg" alt="Status: Active">
  </p>
</p>

---

## 📋 Overview

The **AI Trading Agent Platform** is an end-to-end autonomous trading system designed for **Indian equity derivatives markets** (NIFTY, BANKNIFTY, SENSEX options). It combines **multi-agent intelligence**, **machine learning models**, and **proven trading strategies** to identify high-probability trade setups, manage risk, and execute trades automatically.

### Why This Platform?

| Feature | Benefit |
|---------|---------|
| 🧠 **Multi-Agent Architecture** | 6+ specialized agents work together for consensus-based decisions |
| 📊 **3 Proven Strategies** | VWAP, EMA Crossover, and Opening Range Breakout |
| 🤖 **AI-Powered Predictions** | RandomForest + Reinforcement Learning models |
| ⚡ **Real-time Processing** | WebSocket-based live market data feeds |
| 🛡️ **Risk Management** | Position sizing, daily loss limits, and auto square-off |
| 📈 **Backtesting Engine** | Full historical backtesting with performance analytics |

---

## ✨ Features

### 🔹 Intelligent Agents
- **Market Data Agent** — Real-time and historical data via Flattrade API + WebSocket
- **Scanner Agent** — Scans markets for potential trade setups
- **Feature Engineering Agent** — Computes 14+ technical indicators (RSI, MACD, EMA, VWAP, ATR, ADX, Bollinger Bands, etc.)
- **Regime Detector** — Identifies market regimes (trending, sideways, volatile)
- **Multi-Timeframe Engine** — Analyzes 1m, 5m, and 15m timeframes simultaneously
- **Signal Aggregator** — Combines signals from all agents for consensus-based decisions

### 🔹 Trading Strategies
- **VWAP Strategy** — Volume-Weighted Average Price reversions and breakouts
- **EMA Crossover Strategy** — 9/21 EMA crossover with trend confirmation
- **ORB Strategy** — Opening Range Breakout with momentum validation

### 🔹 AI/ML Models
- **RandomForest Classifier** — Probability-based trade prediction
- **Reinforcement Learning Agent** — DQN-based adaptive decision making
- **Feature set**: RSI, MACD, EMA, VWAP, ATR, Volume Ratio, ADX, Bollinger Bands, Trend Strength

### 🔹 Execution Modes
- **Paper Trading** — Risk-free simulation with realistic execution
- **Live Trading** — Direct order execution via Flattrade API
- **Backtesting** — Historical strategy validation with detailed analytics

### 🔹 Risk Management
- Position sizing based on account capital
- Maximum daily loss limit (configurable, default: ₹400)
- Daily profit target (configurable, default: ₹600)
- Auto square-off before market close (3:20 PM IST)
- Per-trade risk limits (1-2% of capital)

### 🔹 Dashboard & Monitoring
- **Streamlit-powered dashboard** with real-time P&L tracking
- Live positions and order monitoring
- Trade history and performance analytics
- Telegram bot notifications for trade alerts

---

## 🏗️ Architecture

```
ai-trading-agent/
├── agents/                          # Core intelligent agents
│   ├── market_data_agent.py         # Real-time market data feeds
│   ├── scanner_agent.py             # Market scanning & setup detection
│   ├── feature_engineering_agent.py # Technical indicator computation
│   ├── regime_detector.py           # Market regime classification
│   ├── multi_timeframe_engine.py    # Multi-timeframe analysis
│   └── signal_aggregator.py         # Consensus signal generation
│
├── strategies/                      # Trading strategy implementations
│   ├── base_strategy.py             # Abstract base strategy class
│   ├── vwap_strategy.py             # VWAP-based strategy
│   ├── ema_strategy.py              # EMA crossover strategy
│   └── orb_strategy.py              # Opening Range Breakout strategy
│
├── models/                          # AI/ML models
│   ├── ai_prediction_model.py       # RandomForest prediction model
│   └── reinforcement_learning_agent.py  # DQN RL agent
│
├── execution/                       # Trade execution & backtesting
│   ├── flattrade_executor.py        # Live order execution (Flattrade API)
│   ├── paper_trader.py              # Paper trading simulator
│   ├── backtester.py                # Historical backtesting engine
│   ├── backtest_analytics.py        # Backtest performance analysis
│   └── performance_analyzer.py      # P&L and performance metrics
│
├── risk/                            # Risk management
│   └── risk_manager.py              # Position sizing & risk controls
│
├── signals/                         # Signal processing
├── optimizer/                       # Strategy parameter optimization
├── scheduler/                       # Trading schedule automation
├── dashboard/                       # Streamlit web dashboard
│   └── app.py                       # Dashboard application
│
├── documents/                       # Comprehensive documentation
├── config.py                        # Master configuration (all settings)
├── main.py                          # Main entry point & orchestrator
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variable template
└── .gitignore                       # Git ignore rules
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Flattrade trading account** (for live/paper trading)
- **Telegram Bot** (optional, for notifications)

### 1. Clone the Repository

```bash
git clone https://github.com/Indrajithinna/ai-trading-agent.git
cd ai-trading-agent
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Execution Mode: "paper" (safe) or "live" (real money)
EXECUTION_MODE=paper

# Flattrade API Credentials
FLATTRADE_API_KEY=your_api_key_here
FLATTRADE_API_SECRET=your_api_secret_here
FLATTRADE_TOTP_KEY=your_totp_key_here
FLATTRADE_CLIENT_ID=your_client_id_here

# Telegram Notifications (optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 5. Run the Platform

```bash
# Paper Trading Mode (default, safe)
python main.py

# Backtesting Mode
python -c "from execution.backtester import Backtester; Backtester().run()"

# Launch Dashboard
streamlit run dashboard/app.py
```

---

## 📊 Strategies

### VWAP Strategy
Uses Volume-Weighted Average Price as a dynamic support/resistance level. Identifies reversions when price deviates significantly from VWAP, confirmed by RSI and volume spikes.

| Parameter | Default |
|-----------|---------|
| RSI Buy Threshold | 60.0 |
| RSI Sell Threshold | 40.0 |
| Volume Spike Multiplier | 1.5x |

### EMA Crossover Strategy
Trades crossovers between fast (9-period) and slow (21-period) Exponential Moving Averages, filtered by trend direction and ADX strength.

| Parameter | Default |
|-----------|---------|
| Fast EMA | 9 |
| Slow EMA | 21 |
| ADX Threshold | 25.0 |

### Opening Range Breakout (ORB)
Captures momentum breakouts from the first 15-minute price range of the trading session, with volume and trend confirmation.

| Parameter | Default |
|-----------|---------|
| ORB Period | 15 min |
| Breakout Buffer | 0.1% |

---

## ⚙️ Configuration

All platform settings are managed through `config.py` using Python dataclasses:

| Config Class | Purpose |
|-------------|---------|
| `TradingConfig` | Capital, risk limits, trade scoring thresholds |
| `MarketConfig` | Market hours, timeframes, index selection |
| `FlattradeConfig` | Broker API endpoints and credentials |
| `StrategyConfig` | Strategy-specific parameters |
| `AIModelConfig` | ML model hyperparameters |
| `RLConfig` | Reinforcement learning settings |
| `DashboardConfig` | Dashboard host, port, theme |
| `OptimizerConfig` | Strategy optimization methods |
---

## 📖 Documentation

Detailed documentation is available in the [`documents/`](documents/) folder:

| Document | Description |
|----------|-------------|
| [📐 Architecture](documents/ARCHITECTURE.md) | System design and component interactions |
| [🔧 Setup Guide](documents/SETUP_GUIDE.md) | Detailed installation and configuration |
| [📄 Paper Trading Guide](documents/PAPER_TRADING_GUIDE.md) | Risk-free simulation guide |
| [💰 Live Trading Guide](documents/LIVE_TRADING_GUIDE.md) | Live execution setup |
| [📈 Backtesting Guide](documents/BACKTESTING_GUIDE.md) | Historical strategy testing |
| [🔌 API Reference](documents/API_REFERENCE.md) | Complete API documentation |
| [🚀 Deployment](documents/DEPLOYMENT.md) | Production deployment guide |
| [🔮 Future Scope](documents/FUTURE_SCOPE.md) | Roadmap and planned features |
| [📝 Changelog](documents/CHANGELOG.md) | Version history |

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|-------------|
| **Language** | Python 3.10+ |
| **Data Analysis** | Pandas, NumPy |
| **Machine Learning** | Scikit-learn, XGBoost (optional) |
| **Technical Analysis** | Custom indicators, TA-Lib (optional) |
| **Visualization** | Matplotlib, Streamlit |
| **Market Data** | Flattrade API, WebSocket, yfinance |
| **Notifications** | Telegram Bot API |
| **Environment** | python-dotenv |

---

## ⚠️ Disclaimer

> **This software is for educational and research purposes only.** Trading in financial markets involves substantial risk of loss. Past performance (including backtesting results) is not indicative of future results. The authors are not responsible for any financial losses incurred from using this platform. Always start with **paper trading** before risking real capital.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss the proposed change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Built with ❤️ for the Indian trading community</strong>
  <br>
  <sub>If you find this useful, consider giving it a ⭐</sub>
</p>
