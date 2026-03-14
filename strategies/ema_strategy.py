"""
EMA Momentum Strategy (Module 6b)
===================================
EMA9 > EMA21 → BUY CALL
EMA9 < EMA21 → BUY PUT
"""

from typing import Dict, Any

import pandas as pd
import numpy as np

from ai_trading_agent.strategies.base_strategy import BaseStrategy, StrategySignal, SignalType
from ai_trading_agent.config import StrategyConfig
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("EMAStrategy")


class EMAMomentumStrategy(BaseStrategy):
    """
    EMA Momentum Strategy
    
    Rules:
    - BUY CALL: EMA9 crosses above EMA21 (or stays above with momentum)
    - BUY PUT: EMA9 crosses below EMA21 (or stays below with momentum)
    - HOLD: EMAs are converging or flat
    
    Enhanced with MACD confirmation and trend strength filtering.
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__("EMA_MOMENTUM")
        self.config = config
        self.ema_fast = config.ema_fast_period
        self.ema_slow = config.ema_slow_period
        logger.info("EMAMomentumStrategy initialized")
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> StrategySignal:
        """Generate EMA momentum signal."""
        if df.empty or len(df) < 25:
            return self._no_signal(symbol, "Insufficient data")
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Get EMA values
        ema9 = latest.get('EMA9', 0)
        ema21 = latest.get('EMA21', 0)
        ema9_prev = prev.get('EMA9', 0)
        ema21_prev = prev.get('EMA21', 0)
        
        close = latest.get('close', 0)
        atr = latest.get('ATR', 0)
        rsi = latest.get('RSI', 50)
        macd_hist = latest.get('MACD_Hist', 0)
        
        if ema9 == 0 or ema21 == 0:
            return self._no_signal(symbol, "EMA values not available")
        
        indicators = {
            'close': round(close, 2),
            'ema9': round(ema9, 2),
            'ema21': round(ema21, 2),
            'rsi': round(rsi, 2),
            'macd_hist': round(macd_hist, 4),
            'atr': round(atr, 4)
        }
        
        # Detect EMA crossover or strong trend
        ema_cross_up = (ema9 > ema21) and (ema9_prev <= ema21_prev)
        ema_cross_down = (ema9 < ema21) and (ema9_prev >= ema21_prev)
        ema_bullish = ema9 > ema21
        ema_bearish = ema9 < ema21
        
        # EMA separation strength
        ema_diff_pct = abs(ema9 - ema21) / ema21 * 100 if ema21 > 0 else 0
        
        adx = latest.get('Trend_Strength', 0)
        
        # ─── BUY CALL: EMA9 > EMA21 ─────────────────────────
        if ema_bullish and ema_cross_up and rsi > 60 and adx > 25:
            entry = round(close, 2)
            
            signal = StrategySignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY_CALL,
                symbol=symbol,
                confidence=85.0,
                entry_price=entry,
                target1=round(entry + atr * 0.5, 2),
                target2=round(entry + atr * 0.8, 2),
                stop_loss=round(entry - atr * 0.5, 2),
                reason=f"1:1 Conviction EMA UP: Crossover + RSI/ADX",
                indicators=indicators
            )
            self.add_to_history(signal)
            logger.info(f"🟢 {symbol} EMA BUY CALL | 1:1 Scale Focus")
            return signal
        
        # ─── BUY PUT: EMA9 < EMA21 ──────────────────────────
        if ema_bearish and ema_cross_down and rsi < 40 and adx > 25:
            entry = round(close, 2)
            
            signal = StrategySignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY_PUT,
                symbol=symbol,
                confidence=85.0,
                entry_price=entry,
                target1=round(entry - atr * 0.5, 2),
                target2=round(entry - atr * 0.8, 2),
                stop_loss=round(entry + atr * 0.5, 2),
                reason=f"1:1 Conviction EMA DOWN: Crossover + RSI/ADX",
                indicators=indicators
            )
            self.add_to_history(signal)
            logger.info(f"🔴 {symbol} EMA BUY PUT | 1:1 Scale Focus")
            return signal
        
        return self._no_signal(symbol, "No EMA momentum signal")
    
    def _calculate_confidence(self, ema_diff_pct: float, rsi: float, 
                             macd_hist: float, is_crossover: bool, 
                             direction: str) -> float:
        """Calculate signal confidence."""
        score = 0
        
        # EMA separation (max 25 points)
        score += min(25, ema_diff_pct * 50)
        
        # Crossover bonus (15 points)
        if is_crossover:
            score += 15
        
        # RSI confirmation (max 25 points)
        if direction == "CALL":
            if 55 < rsi < 75:
                score += 25
            elif rsi > 50:
                score += 10
        else:
            if 25 < rsi < 45:
                score += 25
            elif rsi < 50:
                score += 10
        
        # MACD confirmation (max 20 points)
        if direction == "CALL" and macd_hist > 0:
            score += min(20, abs(macd_hist) * 100)
        elif direction == "PUT" and macd_hist < 0:
            score += min(20, abs(macd_hist) * 100)
        
        # Base score
        score += 10
        
        return min(100, max(0, score))
    
    def _no_signal(self, symbol: str, reason: str) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            signal_type=SignalType.NO_SIGNAL,
            symbol=symbol,
            confidence=0,
            reason=reason
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
        }
    
    def set_parameters(self, params: Dict[str, Any]):
        if "ema_fast" in params:
            self.ema_fast = params["ema_fast"]
        if "ema_slow" in params:
            self.ema_slow = params["ema_slow"]
        logger.info(f"EMA Strategy parameters updated: {params}")
