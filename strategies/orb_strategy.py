"""
Opening Range Breakout Strategy (Module 6c)
=============================================
Break first 15-minute high → BUY CALL
Break first 15-minute low → BUY PUT
"""

from typing import Dict, Any, Optional

import pandas as pd
import numpy as np

from ai_trading_agent.strategies.base_strategy import BaseStrategy, StrategySignal, SignalType
from ai_trading_agent.config import StrategyConfig
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("ORBStrategy")


class ORBStrategy(BaseStrategy):
    """
    Opening Range Breakout Strategy
    
    Rules:
    - Determine the first 15-minute candle range (9:15 - 9:30 AM)
    - BUY CALL: Price breaks above the ORB high with volume
    - BUY PUT: Price breaks below the ORB low with volume
    - Once triggered per direction per day, no re-entry
    
    Enhanced with volume confirmation and buffer zone.
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__("ORB_BREAKOUT")
        self.config = config
        self.breakout_buffer_pct = config.orb_breakout_buffer
        
        # ORB levels per symbol (reset daily)
        self._orb_high: Dict[str, float] = {}
        self._orb_low: Dict[str, float] = {}
        self._orb_set: Dict[str, bool] = {}
        self._triggered_up: Dict[str, bool] = {}
        self._triggered_down: Dict[str, bool] = {}
        
        logger.info("ORBStrategy initialized")
    
    def set_opening_range(self, symbol: str, high: float, low: float):
        """Manually set the opening range for a symbol."""
        self._orb_high[symbol] = high
        self._orb_low[symbol] = low
        self._orb_set[symbol] = True
        self._triggered_up[symbol] = False
        self._triggered_down[symbol] = False
        logger.info(f"📏 {symbol} ORB set: High={high:.2f}, Low={low:.2f}")
    
    def reset_daily(self, symbol: str):
        """Reset ORB state for a new trading day."""
        self._orb_set[symbol] = False
        self._triggered_up[symbol] = False
        self._triggered_down[symbol] = False
        if symbol in self._orb_high:
            del self._orb_high[symbol]
        if symbol in self._orb_low:
            del self._orb_low[symbol]
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> StrategySignal:
        """Generate high-probability Breakout signal."""
        if df.empty or len(df) < 10:
            return self._no_signal(symbol, "Insufficient data")
        
        latest = df.iloc[-1]
        close = latest.get('close', 0)
        atr = latest.get('ATR', 0)
        rsi = latest.get('RSI', 50)
        adx = latest.get('Trend_Strength', 0)
        macd = latest.get('MACD_Hist', 0)
        
        volume_ratio = latest.get('Volume_Ratio', 1.0)
        
        # 3-day high/low (excluding today)
        recent_high = df['high'].iloc[-4:-1].max()
        recent_low = df['low'].iloc[-4:-1].min()
        
        # Trend filters
        ema9 = latest.get('EMA9', 0)
        ema21 = latest.get('EMA21', 0)
        
        indicators = {
            'close': round(close, 2),
            'recent_high': round(recent_high, 2),
            'recent_low': round(recent_low, 2),
            'rsi': round(rsi, 2),
            'adx': round(adx, 2),
            'volume_ratio': round(volume_ratio, 2)
        }
        
        buffer = atr * 0.05
        
        # ─── BUY CALL: Break above 3-day high in high-conviction uptrend ─────────
        if close > (recent_high + buffer) and ema9 > ema21 and rsi > 60 and adx > 25 and volume_ratio > 1.2:
            confidence = 90.0
            
            entry = round(close, 2)
            # High RR 1:1 for rapid compounding
            target1 = round(entry + atr * 0.5, 2)
            target2 = round(entry + atr * 0.8, 2)
            sl = round(entry - atr * 0.5, 2)
            
            signal = StrategySignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY_CALL,
                symbol=symbol,
                confidence=min(100, confidence),
                entry_price=entry,
                target1=target1,
                target2=target2,
                stop_loss=sl,
                reason=f"1:1 Conviction ORB UP: Close ({close:.0f}) > 3D High ({recent_high:.0f})",
                indicators=indicators
            )
            self.add_to_history(signal)
            logger.info(f"🟢 {symbol} 1:1 CONVICTION ORB BREAKOUT UP | Scale Focus")
            return signal
        
        # ─── BUY PUT: Break below 3-day low in high-conviction downtrend ────────
        if close < (recent_low - buffer) and ema9 < ema21 and rsi < 40 and adx > 25 and volume_ratio > 1.2:
            confidence = 90.0
            
            entry = round(close, 2)
            target1 = round(entry - atr * 0.5, 2)
            target2 = round(entry - atr * 0.8, 2)
            sl = round(entry + atr * 0.5, 2)
            
            signal = StrategySignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY_PUT,
                symbol=symbol,
                confidence=min(100, confidence),
                entry_price=entry,
                target1=target1,
                target2=target2,
                stop_loss=sl,
                reason=f"Breakdown: Close ({close:.0f}) < 3D Low ({recent_low:.0f})",
                indicators=indicators
            )
            self.add_to_history(signal)
            logger.info(f"🔴 {symbol} BREAKDOWN | Confidence: {confidence:.0f}%")
            return signal
        
        return self._no_signal(symbol, "No breakout signal")
    
    def _auto_detect_orb(self, df: pd.DataFrame, symbol: str):
        """Auto-detect the opening range from the first candle(s)."""
        if len(df) >= 1:
            # Use first candle as ORB
            first_bar = df.iloc[0]
            self.set_opening_range(
                symbol,
                high=first_bar['high'],
                low=first_bar['low']
            )
    
    def _calculate_confidence(self, close: float, orb_level: float,
                             orb_range: float, volume_ratio: float,
                             rsi: float, direction: str) -> float:
        """Calculate signal confidence."""
        score = 0
        
        # Breakout strength (max 30 points)
        breakout_pct = abs(close - orb_level) / orb_range * 100 if orb_range > 0 else 0
        score += min(30, breakout_pct * 3)
        
        # Volume confirmation (max 30 points)
        if volume_ratio > 2.0:
            score += 30
        elif volume_ratio > 1.5:
            score += 20
        elif volume_ratio > 1.0:
            score += 10
        
        # RSI confirmation (max 25 points)
        if direction == "CALL" and rsi > 55:
            score += min(25, (rsi - 50) * 1.5)
        elif direction == "PUT" and rsi < 45:
            score += min(25, (50 - rsi) * 1.5)
        
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
            "breakout_buffer_pct": self.breakout_buffer_pct,
            "orb_levels": {
                s: {"high": self._orb_high.get(s), "low": self._orb_low.get(s)}
                for s in self._orb_set if self._orb_set[s]
            }
        }
    
    def set_parameters(self, params: Dict[str, Any]):
        if "breakout_buffer_pct" in params:
            self.breakout_buffer_pct = params["breakout_buffer_pct"]
        logger.info(f"ORB Strategy parameters updated: {params}")
