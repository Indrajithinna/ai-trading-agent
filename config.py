"""
Configuration for AI Trading Agent Platform
All global settings, API keys, trading parameters, and system constants.
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import time


# ─── Trading Parameters ─────────────────────────────────────────────────────
@dataclass
class TradingConfig:
    """Core trading parameters"""
    initial_capital: float = 8000.0
    max_daily_loss: float = 400.0
    daily_profit_target: float = 600.0
    max_trades_per_day: int = 10
    target_win_rate: float = 0.70
    risk_per_trade_min: float = 0.01  # 1%
    risk_per_trade_max: float = 0.02  # 2%
    min_trade_score: float = 70.0
    min_ai_probability: float = 0.70
    min_consensus_agents: int = 3
    total_strategy_agents: int = 4


# ─── Market Configuration ────────────────────────────────────────────────────
@dataclass
class MarketConfig:
    """Indian market configuration"""
    markets: List[str] = field(default_factory=lambda: ["NIFTY", "BANKNIFTY", "SENSEX"])
    market_open: time = time(9, 15)
    market_close: time = time(15, 30)
    square_off_time: time = time(15, 20)
    pre_market_start: time = time(9, 0)
    
    # Timeframe configuration (in minutes)
    trend_timeframe: int = 15
    setup_timeframe: int = 5
    entry_timeframe: int = 1
    
    # Opening Range Breakout
    orb_period_minutes: int = 15


# ─── Flattrade API Configuration ─────────────────────────────────────────────
@dataclass
class FlattradeConfig:
    """Flattrade broker API settings"""
    api_key: str = ""
    api_secret: str = ""
    totp_key: str = ""
    client_id: str = ""
    base_url: str = "https://piconnect.flattrade.in/PiConnectTP"
    ws_url: str = "wss://piconnect.flattrade.in/PiConnectWSTp"
    redirect_url: str = "https://localhost"
    
    # API endpoints
    login_endpoint: str = "/QuickAuth"
    place_order_endpoint: str = "/PlaceOrder"
    modify_order_endpoint: str = "/ModifyOrder"
    cancel_order_endpoint: str = "/CancelOrder"
    order_book_endpoint: str = "/OrderBook"
    positions_endpoint: str = "/PositionBook"
    holdings_endpoint: str = "/Holdings"
    limits_endpoint: str = "/Limits"
    scripinfo_endpoint: str = "/GetSecurityInfo"
    optionchain_endpoint: str = "/GetOptionChain"

    def __post_init__(self):
        self.api_key = os.getenv("FLATTRADE_API_KEY", self.api_key)
        self.api_secret = os.getenv("FLATTRADE_API_SECRET", self.api_secret)
        self.totp_key = os.getenv("FLATTRADE_TOTP_KEY", self.totp_key)
        self.client_id = os.getenv("FLATTRADE_CLIENT_ID", self.client_id)


# ─── Telegram Configuration ──────────────────────────────────────────────────
@dataclass
class TelegramConfig:
    """Telegram bot settings"""
    bot_token: str = ""
    chat_id: str = ""
    parse_mode: str = "HTML"
    
    def __post_init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", self.bot_token)
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", self.chat_id)


# ─── Strategy Parameters ─────────────────────────────────────────────────────
@dataclass
class StrategyConfig:
    """Strategy-specific parameters"""
    # VWAP Strategy
    vwap_rsi_buy_threshold: float = 60.0
    vwap_rsi_sell_threshold: float = 40.0
    vwap_volume_spike_multiplier: float = 1.5
    
    # EMA Strategy
    ema_fast_period: int = 9
    ema_slow_period: int = 21
    
    # ORB Strategy
    orb_breakout_buffer: float = 0.1  # percentage
    
    # Common
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    atr_period: int = 14
    adx_period: int = 14
    volume_ma_period: int = 20
    
    # Regime Detection
    adx_trending_threshold: float = 25.0
    adx_sideways_threshold: float = 20.0
    atr_volatile_multiplier: float = 1.5


# ─── AI Model Configuration ──────────────────────────────────────────────────
@dataclass
class AIModelConfig:
    """Machine learning model parameters"""
    features: List[str] = field(default_factory=lambda: [
        "RSI", "MACD", "EMA9", "EMA21", "VWAP", "ATR", "Volume",
        "MACD_Signal", "MACD_Hist", "ADX", "BB_Upper", "BB_Lower",
        "Volume_Ratio", "Trend_Strength"
    ])
    
    # RandomForest params
    rf_n_estimators: int = 100
    rf_max_depth: int = 10
    rf_min_samples_split: int = 5
    
    # XGBoost params
    xgb_n_estimators: int = 100
    xgb_max_depth: int = 6
    xgb_learning_rate: float = 0.1
    
    # Training
    test_size: float = 0.2
    retrain_interval_days: int = 7
    model_save_path: str = "models/saved/"


# ─── Reinforcement Learning Configuration ────────────────────────────────────
@dataclass
class RLConfig:
    """Reinforcement Learning agent parameters"""
    state_features: List[str] = field(default_factory=lambda: [
        "rsi", "macd", "ema_diff", "vwap_diff", "atr",
        "volume_ratio", "trend_strength", "volatility",
        "position_status", "unrealized_pnl"
    ])
    actions: List[str] = field(default_factory=lambda: ["BUY_CALL", "BUY_PUT", "HOLD"])
    
    learning_rate: float = 0.001
    gamma: float = 0.99
    epsilon_start: float = 1.0
    epsilon_end: float = 0.01
    epsilon_decay: float = 0.995
    memory_size: int = 10000
    batch_size: int = 32
    episodes: int = 1000


# ─── Dashboard Configuration ─────────────────────────────────────────────────
@dataclass 
class DashboardConfig:
    """Streamlit dashboard settings"""
    host: str = "0.0.0.0"
    port: int = 8501
    theme: str = "dark"
    refresh_interval: int = 5  # seconds


# ─── Optimization Configuration ──────────────────────────────────────────────
@dataclass
class OptimizerConfig:
    """Strategy optimizer settings"""
    methods: List[str] = field(default_factory=lambda: ["grid_search", "random_search", "genetic_algorithm"])
    optimization_interval_days: int = 7
    population_size: int = 50
    generations: int = 100
    mutation_rate: float = 0.1
    crossover_rate: float = 0.7


# ─── Logging Configuration ───────────────────────────────────────────────────
@dataclass
class LoggingConfig:
    """Logging settings"""
    log_level: str = "INFO"
    log_file: str = "logs/trading_agent.log"
    log_format: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    max_bytes: int = 10_000_000
    backup_count: int = 5


# ─── Master Configuration ────────────────────────────────────────────────────
@dataclass
class MasterConfig:
    """Master configuration combining all sub-configs"""
    trading: TradingConfig = field(default_factory=TradingConfig)
    market: MarketConfig = field(default_factory=MarketConfig)
    flattrade: FlattradeConfig = field(default_factory=FlattradeConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    ai_model: AIModelConfig = field(default_factory=AIModelConfig)
    rl: RLConfig = field(default_factory=RLConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    execution_mode: str = "paper"  # "paper" or "live"
    

def load_config() -> MasterConfig:
    """Load configuration with environment variable overrides"""
    config = MasterConfig()
    
    # Override execution mode from env
    config.execution_mode = os.getenv("EXECUTION_MODE", "paper")
    
    return config
