"""
Market Regime Detection AI (Module 4)
======================================
Classifies market conditions as TRENDING, SIDEWAYS, or VOLATILE.
Dynamically switches strategy parameters based on detected regime.
"""

from enum import Enum
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

import pandas as pd
import numpy as np

from ai_trading_agent.config import StrategyConfig
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("RegimeDetection")


class MarketRegime(Enum):
    TRENDING = "TRENDING"
    SIDEWAYS = "SIDEWAYS"
    VOLATILE = "VOLATILE"


@dataclass
class RegimeInfo:
    """Detailed regime classification result."""
    regime: MarketRegime
    confidence: float  # 0-100
    adx_value: float
    atr_value: float
    atr_percentile: float
    trend_direction: str  # "UP", "DOWN", "FLAT"
    volatility_level: str  # "LOW", "MEDIUM", "HIGH"
    recommended_strategy: str


class MarketRegimeDetector:
    """
    Classifies market into regimes using ADX, ATR, and moving averages.
    
    Regimes:
    - TRENDING: ADX > 25, clear directional bias
    - SIDEWAYS: ADX < 20, range-bound price action
    - VOLATILE: High ATR relative to historical average
    
    The regime affects strategy selection and position sizing.
    """
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self._regime_history: Dict[str, list] = {}
        logger.info("MarketRegimeDetector initialized")
    
    def detect_regime(self, df: pd.DataFrame, symbol: str = "") -> RegimeInfo:
        """
        Detect market regime from OHLC data with technical indicators.
        
        Args:
            df: DataFrame with ADX, ATR, EMA columns computed
            symbol: Symbol name for history tracking
            
        Returns:
            RegimeInfo with classification and metadata
        """
        if df.empty or len(df) < 30:
            return self._default_regime()
        
        # Ensure required indicators exist
        if 'ADX' not in df.columns or 'ATR' not in df.columns:
            logger.warning("ADX/ATR not found in data. Computing from raw OHLC.")
            df = self._compute_basic_indicators(df)
        
        # Get latest values
        adx = df['ADX'].iloc[-1] if not np.isnan(df['ADX'].iloc[-1]) else 20
        atr = df['ATR'].iloc[-1] if not np.isnan(df['ATR'].iloc[-1]) else 0
        
        # Historical ATR percentile
        atr_series = df['ATR'].dropna()
        atr_percentile = (atr_series < atr).mean() * 100 if len(atr_series) > 10 else 50
        
        # Trend direction from EMAs
        trend_direction = self._determine_trend_direction(df)
        
        # Volatility level
        volatility_level = self._classify_volatility(atr_percentile)
        
        # Regime classification
        regime, confidence = self._classify_regime(adx, atr_percentile, df)
        
        # Recommended strategy
        recommended = self._recommend_strategy(regime, trend_direction, volatility_level)
        
        info = RegimeInfo(
            regime=regime,
            confidence=round(confidence, 2),
            adx_value=round(adx, 2),
            atr_value=round(atr, 4),
            atr_percentile=round(atr_percentile, 2),
            trend_direction=trend_direction,
            volatility_level=volatility_level,
            recommended_strategy=recommended
        )
        
        # Track history
        if symbol:
            if symbol not in self._regime_history:
                self._regime_history[symbol] = []
            self._regime_history[symbol].append(info)
            if len(self._regime_history[symbol]) > 100:
                self._regime_history[symbol] = self._regime_history[symbol][-100:]
        
        logger.info(
            f"📊 {symbol} Regime: {regime.value} | "
            f"ADX: {adx:.1f} | ATR%ile: {atr_percentile:.0f} | "
            f"Trend: {trend_direction} | Confidence: {confidence:.0f}%"
        )
        
        return info
    
    def _classify_regime(self, adx: float, atr_percentile: float, 
                         df: pd.DataFrame) -> Tuple[MarketRegime, float]:
        """Classify the market regime with confidence score."""
        
        # Score each regime
        trending_score = 0
        sideways_score = 0
        volatile_score = 0
        
        # ADX-based scoring
        if adx > self.config.adx_trending_threshold:
            trending_score += 40
        elif adx < self.config.adx_sideways_threshold:
            sideways_score += 40
        else:
            trending_score += 15
            sideways_score += 15
        
        # ATR percentile scoring
        if atr_percentile > 75:
            volatile_score += 35
        elif atr_percentile > 50:
            trending_score += 15
            volatile_score += 10
        else:
            sideways_score += 25
        
        # Price action scoring
        if len(df) >= 20:
            # Check if price is making higher highs OR lower lows (trending)
            recent = df.tail(20)
            highs_trending = (recent['high'].diff().tail(10) > 0).sum() >= 7
            lows_trending = (recent['low'].diff().tail(10) < 0).sum() >= 7
            
            if highs_trending or lows_trending:
                trending_score += 25
            else:
                sideways_score += 15
            
            # Range-bound check
            price_range = (recent['high'].max() - recent['low'].min()) / recent['close'].mean() * 100
            if price_range < 1.0:
                sideways_score += 20
            elif price_range > 2.5:
                volatile_score += 20
        
        # Moving average alignment
        if 'EMA9' in df.columns and 'EMA21' in df.columns:
            ema9 = df['EMA9'].iloc[-1]
            ema21 = df['EMA21'].iloc[-1]
            ema_diff_pct = abs(ema9 - ema21) / ema21 * 100
            
            if ema_diff_pct > 0.3:
                trending_score += 15
            else:
                sideways_score += 10
        
        # Determine winning regime
        scores = {
            MarketRegime.TRENDING: trending_score,
            MarketRegime.SIDEWAYS: sideways_score,
            MarketRegime.VOLATILE: volatile_score
        }
        
        regime = max(scores, key=scores.get)
        total_score = sum(scores.values())
        confidence = (scores[regime] / total_score * 100) if total_score > 0 else 50
        
        return regime, confidence
    
    def _determine_trend_direction(self, df: pd.DataFrame) -> str:
        """Determine the trend direction."""
        if len(df) < 10:
            return "FLAT"
        
        # Use EMA if available
        if 'EMA9' in df.columns and 'EMA21' in df.columns:
            ema9 = df['EMA9'].iloc[-1]
            ema21 = df['EMA21'].iloc[-1]
            
            if ema9 > ema21 * 1.001:
                return "UP"
            elif ema9 < ema21 * 0.999:
                return "DOWN"
        
        # Fallback to simple price comparison
        price_change = df['close'].iloc[-1] - df['close'].iloc[-10]
        if price_change > df['close'].iloc[-1] * 0.001:
            return "UP"
        elif price_change < -df['close'].iloc[-1] * 0.001:
            return "DOWN"
        
        return "FLAT"
    
    def _classify_volatility(self, atr_percentile: float) -> str:
        """Classify volatility level."""
        if atr_percentile > 75:
            return "HIGH"
        elif atr_percentile > 40:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _recommend_strategy(self, regime: MarketRegime, trend_dir: str, 
                           vol_level: str) -> str:
        """Recommend strategy based on regime."""
        if regime == MarketRegime.TRENDING:
            if trend_dir == "UP":
                return "EMA_MOMENTUM_LONG"
            elif trend_dir == "DOWN":
                return "EMA_MOMENTUM_SHORT"
            return "VWAP_BREAKOUT"
        
        elif regime == MarketRegime.SIDEWAYS:
            return "ORB_RANGE_BOUND"
        
        elif regime == MarketRegime.VOLATILE:
            if vol_level == "HIGH":
                return "REDUCED_SIZE_TRENDING"
            return "VWAP_BREAKOUT"
        
        return "VWAP_BREAKOUT"
    
    def _compute_basic_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute basic ADX and ATR if not present."""
        # ATR
        if 'ATR' not in df.columns:
            high_low = df['high'] - df['low']
            high_close = (df['high'] - df['close'].shift()).abs()
            low_close = (df['low'] - df['close'].shift()).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(window=14).mean()
        
        # ADX
        if 'ADX' not in df.columns:
            plus_dm = df['high'].diff().clip(lower=0)
            minus_dm = (-df['low'].diff()).clip(lower=0)
            
            tr = pd.concat([
                df['high'] - df['low'],
                (df['high'] - df['close'].shift()).abs(),
                (df['low'] - df['close'].shift()).abs()
            ], axis=1).max(axis=1)
            
            atr14 = tr.rolling(14).mean()
            plus_di = 100 * plus_dm.rolling(14).mean() / atr14.replace(0, np.inf)
            minus_di = 100 * minus_dm.rolling(14).mean() / atr14.replace(0, np.inf)
            
            dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.inf)
            df['ADX'] = dx.rolling(14).mean()
        
        # EMAs
        if 'EMA9' not in df.columns:
            df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
        if 'EMA21' not in df.columns:
            df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
        
        return df
    
    def _default_regime(self) -> RegimeInfo:
        """Return default regime when data is insufficient."""
        return RegimeInfo(
            regime=MarketRegime.SIDEWAYS,
            confidence=30.0,
            adx_value=0.0,
            atr_value=0.0,
            atr_percentile=50.0,
            trend_direction="FLAT",
            volatility_level="MEDIUM",
            recommended_strategy="VWAP_BREAKOUT"
        )
    
    def get_regime_history(self, symbol: str) -> list:
        """Get regime history for a symbol."""
        return self._regime_history.get(symbol, [])
    
    def get_regime_summary(self, symbol: str) -> Dict:
        """Get a summary of regime detection for a symbol."""
        history = self._regime_history.get(symbol, [])
        if not history:
            return {"symbol": symbol, "current": "UNKNOWN", "history_count": 0}
        
        latest = history[-1]
        regime_counts = {}
        for info in history[-20:]:
            r = info.regime.value
            regime_counts[r] = regime_counts.get(r, 0) + 1
        
        return {
            "symbol": symbol,
            "current_regime": latest.regime.value,
            "confidence": latest.confidence,
            "trend_direction": latest.trend_direction,
            "adx": latest.adx_value,
            "volatility": latest.volatility_level,
            "regime_distribution_20": regime_counts,
            "history_count": len(history)
        }
