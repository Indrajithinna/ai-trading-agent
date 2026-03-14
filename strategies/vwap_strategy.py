"""
VWAP Breakout Strategy (Module 6a)
====================================
BUY CALL when: price > VWAP, RSI > 60, volume spike
BUY PUT when: price < VWAP, RSI < 40
"""

from typing import Dict, Any

import pandas as pd
import numpy as np

from ai_trading_agent.strategies.base_strategy import BaseStrategy, StrategySignal, SignalType
from ai_trading_agent.config import StrategyConfig
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("VWAPStrategy")


class VWAPBreakoutStrategy(BaseStrategy):
    """
    VWAP Breakout Strategy
    
    Rules:
    - BUY CALL: Price closes above VWAP + RSI > 60 + Volume spike (1.5x avg)
    - BUY PUT: Price closes below VWAP + RSI < 40
    - HOLD: Otherwise
    
    The strategy uses VWAP as a dynamic support/resistance and combines
    with RSI momentum and volume confirmation.
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__("VWAP_BREAKOUT")
        self.config = config
        self.rsi_buy_threshold = config.vwap_rsi_buy_threshold
        self.rsi_sell_threshold = config.vwap_rsi_sell_threshold
        self.volume_spike_multiplier = config.vwap_volume_spike_multiplier
        logger.info("VWAPBreakoutStrategy initialized")
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> StrategySignal:
        """Generate VWAP breakout signal."""
        if df.empty or len(df) < 20:
            return self._no_signal(symbol, "Insufficient data")
        
        # Get latest values
        latest = df.iloc[-1]
        
        # Required indicators
        close = latest.get('close', 0)
        vwap = latest.get('VWAP', close)
        rsi = latest.get('RSI', 50)
        volume_ratio = latest.get('Volume_Ratio', 1.0)
        atr = latest.get('ATR', 0)
        
        indicators = {
            'close': round(close, 2),
            'vwap': round(vwap, 2),
            'rsi': round(rsi, 2),
            'volume_ratio': round(volume_ratio, 2),
            'atr': round(atr, 4)
        }
        
        # Filter with EMA
        ema9 = latest.get('EMA9', 0)
        ema21 = latest.get('EMA21', 0)
        
        ema9 = latest.get('EMA9', 0)
        ema21 = latest.get('EMA21', 0)
        volume_ratio = latest.get('Volume_Ratio', 1.0)
        
        # ─── BUY CALL Conditions ─────────────────────────────
        if close > vwap and ema9 > ema21 and rsi > 60 and volume_ratio > 1.2:
            # High RR 1:1 for rapid compounding
            entry = round(close, 2)
            sl_dist = atr * 0.5 if atr > 0 else close * 0.005
            target1_dist = atr * 0.5 if atr > 0 else close * 0.005
            target2_dist = atr * 0.8 if atr > 0 else close * 0.008
            
            signal = StrategySignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY_CALL,
                symbol=symbol,
                confidence=85.0,
                entry_price=entry,
                target1=round(entry + target1_dist, 2),
                target2=round(entry + target2_dist, 2),
                stop_loss=round(entry - sl_dist, 2),
                reason=f"1:1 Conviction VWAP UP: Close ({close:.0f}) > VWAP",
                indicators=indicators
            )
            self.add_to_history(signal)
            logger.info(f"🟢 {symbol} VWAP BUY CALL | 1:1 Scale Focus")
            return signal
        
        # ─── BUY PUT Conditions ──────────────────────────────
        if close < vwap and ema9 < ema21 and rsi < 40 and volume_ratio > 1.2:
            entry = round(close, 2)
            sl_dist = atr * 0.5 if atr > 0 else close * 0.005
            target1_dist = atr * 0.5 if atr > 0 else close * 0.005
            target2_dist = atr * 0.8 if atr > 0 else close * 0.008
            
            signal = StrategySignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY_PUT,
                symbol=symbol,
                confidence=85.0,
                entry_price=entry,
                target1=round(entry - target1_dist, 2),
                target2=round(entry - target2_dist, 2),
                stop_loss=round(entry + sl_dist, 2),
                reason=f"1:1 Conviction VWAP DOWN: Close ({close:.0f}) < VWAP",
                indicators=indicators
            )
            self.add_to_history(signal)
            logger.info(f"🔴 {symbol} VWAP BUY PUT | 1:1 Scale Focus")
            return signal
        
        return self._no_signal(symbol, "No VWAP signal conditions met")
    
    def _calculate_confidence(self, close: float, vwap: float, rsi: float, 
                             volume_ratio: float, direction: str) -> float:
        """Calculate signal confidence score."""
        score = 0
        
        # VWAP distance (max 30 points)
        vwap_pct = abs(close - vwap) / vwap * 100
        score += min(30, vwap_pct * 15)
        
        # RSI strength (max 30 points)
        if direction == "CALL":
            rsi_score = max(0, (rsi - 50)) * 0.6
        else:
            rsi_score = max(0, (50 - rsi)) * 0.6
        score += min(30, rsi_score)
        
        # Volume confirmation (max 25 points)
        if volume_ratio > 2.0:
            score += 25
        elif volume_ratio > 1.5:
            score += 15
        elif volume_ratio > 1.0:
            score += 5
        
        # Price action bonus (max 15 points)
        score += 10  # Base presence
        
        return min(100, max(0, score))
    
    def _no_signal(self, symbol: str, reason: str) -> StrategySignal:
        """Generate a no-signal response."""
        return StrategySignal(
            strategy_name=self.name,
            signal_type=SignalType.NO_SIGNAL,
            symbol=symbol,
            confidence=0,
            reason=reason
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "rsi_buy_threshold": self.rsi_buy_threshold,
            "rsi_sell_threshold": self.rsi_sell_threshold,
            "volume_spike_multiplier": self.volume_spike_multiplier
        }
    
    def set_parameters(self, params: Dict[str, Any]):
        if "rsi_buy_threshold" in params:
            self.rsi_buy_threshold = params["rsi_buy_threshold"]
        if "rsi_sell_threshold" in params:
            self.rsi_sell_threshold = params["rsi_sell_threshold"]
        if "volume_spike_multiplier" in params:
            self.volume_spike_multiplier = params["volume_spike_multiplier"]
        logger.info(f"VWAP Strategy parameters updated: {params}")
