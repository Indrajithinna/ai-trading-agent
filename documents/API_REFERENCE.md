# 📚 API Reference

Module-by-module API documentation for the AI Trading Agent Platform.

---

## Table of Contents

1. [Configuration](#1-configuration)
2. [Market Data Agent](#2-market-data-agent)
3. [Feature Engineering Agent](#3-feature-engineering-agent)
4. [Market Scanner Agent](#4-market-scanner-agent)
5. [Market Regime Detector](#5-market-regime-detector)
6. [Multi-Timeframe Engine](#6-multi-timeframe-engine)
7. [Strategy Agents](#7-strategy-agents)
8. [AI Prediction Model](#8-ai-prediction-model)
9. [RL Trading Agent](#9-rl-trading-agent)
10. [Signal Aggregator & Score Engine](#10-signal-aggregator--score-engine)
11. [Risk Manager](#11-risk-manager)
12. [Paper Trader](#12-paper-trader)
13. [Performance Analyzer](#13-performance-analyzer)
14. [Telegram Alert System](#14-telegram-alert-system)
15. [Backtesting Engine](#15-backtesting-engine)

---

## 1. Configuration

**File**: `config.py`

### `MasterConfig`

Top-level configuration combining all sub-configs.

```python
from ai_trading_agent.config import load_config

config = load_config()
config.trading.initial_capital      # 8000.0
config.market.markets               # ["NIFTY", "BANKNIFTY", "SENSEX"]
config.strategy.rsi_period          # 14
config.execution_mode               # "paper"
```

| Sub-Config | Key Fields |
|---|---|
| `TradingConfig` | `initial_capital`, `max_daily_loss`, `daily_profit_target`, `max_trades_per_day`, `min_trade_score` |
| `MarketConfig` | `markets`, `market_open`, `market_close`, `square_off_time`, `trend_timeframe` |
| `FlattradeConfig` | `api_key`, `api_secret`, `totp_key`, `client_id`, `base_url` |
| `TelegramConfig` | `bot_token`, `chat_id` |
| `StrategyConfig` | `vwap_rsi_buy_threshold`, `ema_fast_period`, `orb_breakout_buffer`, `rsi_period`, `atr_period` |
| `AIModelConfig` | `features`, `rf_n_estimators`, `xgb_max_depth`, `test_size` |
| `RLConfig` | `state_features`, `actions`, `learning_rate`, `gamma`, `epsilon_start` |
| `OptimizerConfig` | `methods`, `population_size`, `generations`, `mutation_rate` |

---

## 2. Market Data Agent

**File**: `agents/market_data_agent.py`

### `MarketDataAgent(flattrade_config, market_config)`

```python
agent = MarketDataAgent(config.flattrade, config.market)
```

| Method | Returns | Description |
|--------|---------|-------------|
| `authenticate()` | `bool` | Authenticate with Flattrade (falls back to simulation) |
| `get_spot_price(symbol)` | `float` | Current spot price |
| `get_ohlc_data(symbol, timeframe, bars)` | `DataFrame` | OHLCV data with columns: `open, high, low, close, volume` |
| `get_option_chain(symbol, expiry)` | `DataFrame` | Option chain with strikes, CE/PE prices, OI, IV |
| `start_streaming()` | `None` | Start real-time tick streaming (WebSocket or simulated) |
| `stop_streaming()` | `None` | Stop streaming |
| `subscribe_ticks(symbols, callback)` | `None` | Register callback for tick updates |
| `subscribe_bars(timeframe, callback)` | `None` | Register callback for bar completions |

### Data Classes

```python
MarketTick(symbol, ltp, open, high, low, close, volume, oi, timestamp, bid, ask)
OHLCBar(symbol, timeframe, open, high, low, close, volume, timestamp)
```

---

## 3. Feature Engineering Agent

**File**: `agents/feature_engineering_agent.py`

### `FeatureEngineeringAgent()`

```python
engine = FeatureEngineeringAgent()
df_features = engine.compute_all_features(df_ohlcv, symbol="NIFTY")
```

| Method | Returns | Description |
|--------|---------|-------------|
| `compute_all_features(df, symbol)` | `DataFrame` | Adds 30+ indicator columns to the input DataFrame |
| `get_feature_vector(df, feature_names)` | `DataFrame` | Extract specific features for ML models |
| `get_latest_features(symbol)` | `dict \| None` | Get cached latest feature values |

### Computed Features

| Category | Indicators |
|----------|-----------|
| **Trend** | RSI, EMA9, EMA21, EMA_Diff, EMA_Cross, ADX, Plus_DI, Minus_DI, Trend_Strength, Trend_Direction |
| **Momentum** | MACD, MACD_Signal, MACD_Hist, ROC_5, ROC_10, Stoch_K, Stoch_D |
| **Volatility** | ATR, ATR_Pct, BB_Upper, BB_Lower, BB_Middle, BB_Width, BB_Position |
| **Volume** | VWAP, VWAP_Diff, Volume_MA20, Volume_Ratio, Volume_Spike, OBV, OBV_MA |
| **Patterns** | Is_Doji, Is_Hammer, Is_ShootingStar, Bullish_Engulfing, Bearish_Engulfing |
| **Derived** | Price_Above_EMA9, Price_Above_EMA21, Higher_High, Lower_Low |

---

## 4. Market Scanner Agent

**File**: `agents/scanner_agent.py`

### `MarketScannerAgent(market_data, strategy_config)`

| Method | Returns | Description |
|--------|---------|-------------|
| `scan_all_markets(symbols)` | `list[ScanResult]` | Run all scanners on all symbols |
| `get_top_opportunities(n)` | `list[ScanResult]` | Get top N opportunities by strength |

### Scan Types

- **Momentum** — RSI-based directional moves
- **Volume** — Unusual volume spikes
- **Breakout** — Price breaking consolidation zones
- **Reversal** — Potential reversal setups

---

## 5. Market Regime Detector

**File**: `agents/regime_detector.py`

### `MarketRegimeDetector(strategy_config)`

```python
regime_info = detector.detect_regime(df_features, symbol="NIFTY")
regime_info.regime       # MarketRegime.TRENDING
regime_info.confidence   # 85.0
regime_info.recommended_strategy  # "EMA_MOMENTUM"
```

| Regime | ADX Condition | Recommended Strategy |
|--------|-------------|---------------------|
| `TRENDING` | ADX > 25 | EMA Momentum |
| `SIDEWAYS` | ADX < 20 | VWAP Breakout |
| `VOLATILE` | ATR > 1.5x average | ORB Breakout |

---

## 6. Multi-Timeframe Engine

**File**: `agents/multi_timeframe_engine.py`

### `MultiTimeframeEngine(market_data, feature_engine)`

```python
result = mtf_engine.analyze(symbol="NIFTY")
result.trade_allowed   # True/False
result.alignment       # "BULLISH" / "BEARISH" / "MIXED"
```

Checks alignment across:
- **15m** — Trend direction
- **5m** — Setup confirmation
- **1m** — Entry timing

---

## 7. Strategy Agents

**Files**: `strategies/vwap_strategy.py`, `ema_strategy.py`, `orb_strategy.py`

All strategies extend `BaseStrategy` and implement:

```python
signal = strategy.generate_signal(df_features, symbol)
signal.signal_type    # SignalType.BUY_CALL / BUY_PUT / HOLD / NO_SIGNAL
signal.confidence     # 0–100
signal.entry_price    # Suggested entry
signal.target1        # Target 1
signal.target2        # Target 2
signal.stop_loss      # Stop loss
signal.is_actionable  # True if BUY_CALL or BUY_PUT
```

---

## 8. AI Prediction Model

**File**: `models/ai_prediction_model.py`

### `AIPredictionModel(ai_model_config)`

```python
result = model.predict(df_features)
result['prediction']    # "BUY_CALL" / "BUY_PUT" / "HOLD"
result['probability']   # 0.0–1.0
result['confidence']    # 0–100
```

| Method | Description |
|--------|-------------|
| `train(df, target_col)` | Train on labeled data |
| `predict(features)` | Get prediction + probability |
| `get_feature_importance()` | Feature importance ranking |

---

## 9. RL Trading Agent

**File**: `models/reinforcement_learning_agent.py`

### `RLTradingAgent(rl_config)`

```python
result = rl_agent.predict(raw_state)
result['action']      # "BUY_CALL" / "BUY_PUT" / "HOLD"
result['confidence']  # 0–100
```

| Method | Description |
|--------|-------------|
| `predict(raw_state)` | Get action recommendation from current market state |
| `learn(state, action, reward, next_state, done)` | Q-learning update |
| `save(path)` | Save agent state |
| `load(path)` | Load agent state |

---

## 10. Signal Aggregator & Score Engine

**File**: `agents/signal_aggregator.py`

### `SignalAggregator(trading_config)`

```python
result = aggregator.aggregate(strategy_signals, symbol)
result['consensus_met']           # True/False
result['confirming_count']        # 3 of 4
result['confirming_strategies']   # ["VWAP", "EMA", "ORB"]
result['direction']               # "BUY_CALL"
```

### `TradeScoreEngine(trading_config)`

```python
score = engine.compute_score(aggregation, regime_info, mtf_result, ai_prediction, features)
# Returns: float 0–100
```

### `SmartStrikeSelector(trading_config)`

```python
strike_info = selector.select_strike(symbol, spot_price, direction, confidence, option_chain)
strike_info['strike']       # 24300
strike_info['option_type']  # "CE"
strike_info['entry_price']  # 120.50
```

---

## 11. Risk Manager

**File**: `risk/risk_manager.py`

### `RiskManager(trading_config)`

| Method | Returns | Description |
|--------|---------|-------------|
| `check_trade_allowed()` | `dict` | Check if trading is allowed (capital, loss, trade count) |
| `calculate_position_size(entry, sl)` | `dict` | Calculate optimal position size |
| `record_trade(trade)` | `None` | Record completed trade and update risk state |
| `get_risk_status()` | `dict` | Full risk status snapshot |

---

## 12. Paper Trader

**File**: `execution/paper_trader.py`

### `PaperTradingEngine(trading_config, risk_manager)`

| Method | Returns | Description |
|--------|---------|-------------|
| `execute_signal(signal)` | `PaperPosition \| None` | Simulate trade execution |
| `update_positions(market_prices)` | `None` | Update SL/TP on open positions |
| `square_off_all(reason)` | `None` | Close all open positions |
| `get_portfolio_status()` | `dict` | Balance, P&L, positions |
| `save_state()` | `None` | Save state to JSON |
| `load_state()` | `bool` | Restore from JSON |

---

## 13. Performance Analyzer

**File**: `execution/performance_analyzer.py`

### `PerformanceAnalyzer()`

| Method | Returns | Description |
|--------|---------|-------------|
| `record_trade(trade)` | `None` | Record a trade for analysis |
| `get_summary()` | `dict` | All metrics: win rate, Sharpe, Sortino, drawdown, etc. |
| `get_strategy_breakdown()` | `dict` | Per-strategy performance |
| `save_report()` | `None` | Save daily report to JSON |

---

## 14. Telegram Alert System

**File**: `signals/telegram_alert.py`

### `TelegramAlertSystem(telegram_config)`

| Method | Returns | Description |
|--------|---------|-------------|
| `send_trade_signal(signal)` | `bool` | Send formatted trade signal |
| `send_trade_update(update)` | `bool` | Send target/SL hit update |
| `send_daily_summary(summary)` | `bool` | Send EOD summary |
| `send_system_alert(type, message)` | `bool` | Send system status alert |

---

## 15. Backtesting Engine

**File**: `execution/backtester.py`

### `BacktestEngine(symbols, years, initial_capital, position_size_pct)`

```python
from ai_trading_agent.execution.backtester import BacktestEngine

engine = BacktestEngine(symbols=["NIFTY"], years=5, initial_capital=100000)
report = engine.run()
```

| Method | Returns | Description |
|--------|---------|-------------|
| `run()` | `dict` | Execute full backtest and return analytics report |

### Report Structure

```python
report = {
    "meta": { "symbols", "years", "initial_capital", "total_bars_processed" },
    "summary": { "total_trades", "win_rate", "net_pnl", "sharpe_ratio", ... },
    "strategy_breakdown": { "VWAP": {...}, "EMA": {...}, "ORB": {...} },
    "exit_reason_breakdown": { "TARGET1": N, "STOPLOSS": N, ... },
    "monthly_pnl": { "2021-01": 123.45, ... },
    "yearly_pnl": { "2021": 1234.56, ... },
    "equity_curve": { "dates": [...], "values": [...] },
    "trades": [ {...}, ... ]
}
```
