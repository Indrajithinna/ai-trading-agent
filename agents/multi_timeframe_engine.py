"""
Multi-Timeframe Analysis Engine (Module 5)
============================================
Analyzes 15-minute (trend), 5-minute (setup), 1-minute (entry) timeframes.
Only allows trades when all three timeframes align.
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import numpy as np

from ai_trading_agent.agents.market_data_agent import MarketDataAgent
from ai_trading_agent.agents.feature_engineering_agent import FeatureEngineeringAgent
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("MultiTimeframe")


class TimeframeBias(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass
class TimeframeAnalysis:
    """Analysis result for a single timeframe."""
    timeframe: int  # minutes
    bias: TimeframeBias
    strength: float  # 0-100
    ema_trend: str  # "UP", "DOWN", "FLAT"
    rsi: float
    vwap_position: str  # "ABOVE", "BELOW"
    volume_status: str  # "NORMAL", "HIGH", "LOW"
    key_levels: Dict[str, float] = field(default_factory=dict)


@dataclass
class MTFResult:
    """Multi-timeframe analysis result."""
    symbol: str
    aligned: bool  # All timeframes agree
    overall_bias: TimeframeBias
    confidence: float
    trend_tf: TimeframeAnalysis  # 15-min
    setup_tf: TimeframeAnalysis  # 5-min
    entry_tf: TimeframeAnalysis  # 1-min
    trade_allowed: bool


class MultiTimeframeEngine:
    """
    Analyzes market across three timeframes for trade confirmation.
    
    Timeframes:
    - 15-minute: Identifies the primary trend direction
    - 5-minute: Identifies the setup/intermediate action
    - 1-minute: Times the entry
    
    Trade execution only when all three align in the same direction.
    """
    
    def __init__(self, market_data: MarketDataAgent, feature_engine: FeatureEngineeringAgent):
        self.market_data = market_data
        self.feature_engine = feature_engine
        self._results: Dict[str, MTFResult] = {}
        logger.info("MultiTimeframeEngine initialized")
    
    def analyze(self, symbol: str) -> MTFResult:
        """
        Perform multi-timeframe analysis for a symbol.
        
        Args:
            symbol: Trading symbol (NIFTY, BANKNIFTY, SENSEX)
            
        Returns:
            MTFResult with alignment status and individual timeframe analyses
        """
        # Get data for each timeframe
        df_15m = self.market_data.get_ohlc_data(symbol, 15, 50)
        df_5m = self.market_data.get_ohlc_data(symbol, 5, 100)
        df_1m = self.market_data.get_ohlc_data(symbol, 1, 100)
        
        # Compute features
        df_15m = self.feature_engine.compute_all_features(df_15m, f"{symbol}_15m")
        df_5m = self.feature_engine.compute_all_features(df_5m, f"{symbol}_5m")
        df_1m = self.feature_engine.compute_all_features(df_1m, f"{symbol}_1m")
        
        # Analyze each timeframe
        trend_analysis = self._analyze_timeframe(df_15m, 15)
        setup_analysis = self._analyze_timeframe(df_5m, 5)
        entry_analysis = self._analyze_timeframe(df_1m, 1)
        
        # Check alignment
        aligned = self._check_alignment(trend_analysis, setup_analysis, entry_analysis)
        
        # Determine overall bias
        overall_bias, confidence = self._compute_overall_bias(
            trend_analysis, setup_analysis, entry_analysis
        )
        
        # Trade permission
        trade_allowed = aligned and confidence >= 60
        
        result = MTFResult(
            symbol=symbol,
            aligned=aligned,
            overall_bias=overall_bias,
            confidence=round(confidence, 2),
            trend_tf=trend_analysis,
            setup_tf=setup_analysis,
            entry_tf=entry_analysis,
            trade_allowed=trade_allowed
        )
        
        self._results[symbol] = result
        
        status = "✅ ALIGNED" if aligned else "❌ NOT ALIGNED"
        logger.info(
            f"🔄 {symbol} MTF: {status} | "
            f"15m: {trend_analysis.bias.value} | "
            f"5m: {setup_analysis.bias.value} | "
            f"1m: {entry_analysis.bias.value} | "
            f"Confidence: {confidence:.0f}%"
        )
        
        return result
    
    def _analyze_timeframe(self, df: pd.DataFrame, timeframe: int) -> TimeframeAnalysis:
        """Analyze a single timeframe."""
        if df.empty or len(df) < 5:
            return TimeframeAnalysis(
                timeframe=timeframe,
                bias=TimeframeBias.NEUTRAL,
                strength=0,
                ema_trend="FLAT",
                rsi=50,
                vwap_position="ABOVE",
                volume_status="NORMAL"
            )
        
        # EMA trend
        ema_trend = "FLAT"
        if 'EMA9' in df.columns and 'EMA21' in df.columns:
            ema9 = df['EMA9'].iloc[-1]
            ema21 = df['EMA21'].iloc[-1]
            if ema9 > ema21 * 1.0005:
                ema_trend = "UP"
            elif ema9 < ema21 * 0.9995:
                ema_trend = "DOWN"
        
        # RSI
        rsi = df['RSI'].iloc[-1] if 'RSI' in df.columns else 50
        
        # VWAP position
        vwap_position = "ABOVE"
        if 'VWAP' in df.columns:
            vwap_position = "ABOVE" if df['close'].iloc[-1] > df['VWAP'].iloc[-1] else "BELOW"
        
        # Volume status
        volume_status = "NORMAL"
        if 'Volume_Ratio' in df.columns:
            vol_ratio = df['Volume_Ratio'].iloc[-1]
            if vol_ratio > 1.5:
                volume_status = "HIGH"
            elif vol_ratio < 0.5:
                volume_status = "LOW"
        
        # Determine bias
        bullish_score = 0
        bearish_score = 0
        
        if ema_trend == "UP":
            bullish_score += 30
        elif ema_trend == "DOWN":
            bearish_score += 30
        
        if rsi > 55:
            bullish_score += 20
        elif rsi < 45:
            bearish_score += 20
        
        if vwap_position == "ABOVE":
            bullish_score += 25
        else:
            bearish_score += 25
        
        if volume_status == "HIGH":
            # Volume confirms the direction
            if bullish_score > bearish_score:
                bullish_score += 15
            else:
                bearish_score += 15
        
        # MACD
        if 'MACD_Hist' in df.columns:
            macd_hist = df['MACD_Hist'].iloc[-1]
            if macd_hist > 0:
                bullish_score += 10
            elif macd_hist < 0:
                bearish_score += 10
        
        # Determine final bias
        if bullish_score > bearish_score + 15:
            bias = TimeframeBias.BULLISH
            strength = min(100, bullish_score)
        elif bearish_score > bullish_score + 15:
            bias = TimeframeBias.BEARISH
            strength = min(100, bearish_score)
        else:
            bias = TimeframeBias.NEUTRAL
            strength = max(bullish_score, bearish_score) * 0.5
        
        # Key levels
        key_levels = {}
        if 'VWAP' in df.columns:
            key_levels['vwap'] = round(df['VWAP'].iloc[-1], 2)
        if 'BB_Upper' in df.columns:
            key_levels['bb_upper'] = round(df['BB_Upper'].iloc[-1], 2)
            key_levels['bb_lower'] = round(df['BB_Lower'].iloc[-1], 2)
        key_levels['high'] = round(df['high'].max(), 2)
        key_levels['low'] = round(df['low'].min(), 2)
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            bias=bias,
            strength=round(strength, 2),
            ema_trend=ema_trend,
            rsi=round(rsi, 2),
            vwap_position=vwap_position,
            volume_status=volume_status,
            key_levels=key_levels
        )
    
    def _check_alignment(self, trend: TimeframeAnalysis, 
                         setup: TimeframeAnalysis, 
                         entry: TimeframeAnalysis) -> bool:
        """Check if all three timeframes are aligned."""
        biases = [trend.bias, setup.bias, entry.bias]
        
        # Remove NEUTRAL entries - they don't block alignment
        non_neutral = [b for b in biases if b != TimeframeBias.NEUTRAL]
        
        if len(non_neutral) == 0:
            return False
        
        # Check if all non-neutral biases agree
        return len(set(non_neutral)) == 1
    
    def _compute_overall_bias(self, trend: TimeframeAnalysis, 
                              setup: TimeframeAnalysis,
                              entry: TimeframeAnalysis) -> Tuple[TimeframeBias, float]:
        """Compute weighted overall bias with confidence."""
        # Weights: 15m (40%), 5m (35%), 1m (25%)
        weights = {15: 0.40, 5: 0.35, 1: 0.25}
        
        bullish_score = 0
        bearish_score = 0
        
        for analysis in [trend, setup, entry]:
            w = weights.get(analysis.timeframe, 0.33)
            if analysis.bias == TimeframeBias.BULLISH:
                bullish_score += analysis.strength * w
            elif analysis.bias == TimeframeBias.BEARISH:
                bearish_score += analysis.strength * w
        
        total = bullish_score + bearish_score
        
        if bullish_score > bearish_score:
            confidence = (bullish_score / total * 100) if total > 0 else 50
            return TimeframeBias.BULLISH, confidence
        elif bearish_score > bullish_score:
            confidence = (bearish_score / total * 100) if total > 0 else 50
            return TimeframeBias.BEARISH, confidence
        else:
            return TimeframeBias.NEUTRAL, 50.0
    
    def get_result(self, symbol: str) -> Optional[MTFResult]:
        """Get the latest MTF analysis result for a symbol."""
        return self._results.get(symbol)
    
    def get_summary(self, symbol: str) -> Dict:
        """Get a human-readable summary of MTF analysis."""
        result = self._results.get(symbol)
        if not result:
            return {"symbol": symbol, "status": "NO_DATA"}
        
        return {
            "symbol": symbol,
            "aligned": result.aligned,
            "overall_bias": result.overall_bias.value,
            "confidence": result.confidence,
            "trade_allowed": result.trade_allowed,
            "timeframes": {
                "15m_trend": result.trend_tf.bias.value,
                "5m_setup": result.setup_tf.bias.value,
                "1m_entry": result.entry_tf.bias.value,
            },
            "15m_rsi": result.trend_tf.rsi,
            "5m_rsi": result.setup_tf.rsi,
            "1m_rsi": result.entry_tf.rsi,
        }
