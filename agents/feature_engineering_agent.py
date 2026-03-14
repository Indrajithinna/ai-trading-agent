"""
Feature Engineering Agent (Module 3)
=====================================
Computes technical indicators and engineered features from raw market data.
Provides feature vectors for ML models and strategy agents.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

import pandas as pd
import numpy as np

from ai_trading_agent.utils.logger import get_logger

logger = get_logger("FeatureEngineeringAgent")


class FeatureEngineeringAgent:
    """
    Computes and manages all technical indicators and features.
    
    Indicators:
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - EMA (Exponential Moving Average - 9, 21)
    - VWAP (Volume Weighted Average Price)
    - ATR (Average True Range)
    - ADX (Average Directional Index)
    - Bollinger Bands
    - Volume analysis
    """
    
    def __init__(self):
        self._feature_cache: Dict[str, pd.DataFrame] = {}
        logger.info("FeatureEngineeringAgent initialized")
    
    def compute_all_features(self, df: pd.DataFrame, symbol: str = "") -> pd.DataFrame:
        """
        Compute all technical indicators and features.
        
        Args:
            df: DataFrame with columns [open, high, low, close, volume]
            symbol: Optional symbol name for caching
            
        Returns:
            DataFrame with all features added
        """
        if df.empty or len(df) < 30:
            logger.warning(f"Insufficient data for feature engineering ({len(df)} rows)")
            return df
        
        result = df.copy()
        
        # Price-based indicators
        result = self._compute_rsi(result)
        result = self._compute_macd(result)
        result = self._compute_ema(result)
        result = self._compute_bollinger_bands(result)
        
        # Volatility indicators
        result = self._compute_atr(result)
        result = self._compute_adx(result)
        
        # Volume indicators
        result = self._compute_vwap(result)
        result = self._compute_volume_features(result)
        
        # Derived features
        result = self._compute_trend_features(result)
        result = self._compute_momentum_features(result)
        result = self._compute_pattern_features(result)
        
        # Drop NaN rows from indicator warm-up
        result = result.dropna()
        
        if symbol:
            self._feature_cache[symbol] = result
        
        logger.debug(f"Computed {len(result.columns) - len(df.columns)} features for {symbol or 'data'}")
        return result
    
    def _compute_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Compute RSI (Relative Strength Index)."""
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.inf)
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df
    
    def _compute_macd(self, df: pd.DataFrame, 
                      fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Compute MACD (Moving Average Convergence Divergence)."""
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        
        df['MACD'] = ema_fast - ema_slow
        df['MACD_Signal'] = df['MACD'].ewm(span=signal, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        return df
    
    def _compute_ema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute EMA9 and EMA21."""
        df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['EMA_Diff'] = df['EMA9'] - df['EMA21']
        df['EMA_Cross'] = np.where(
            (df['EMA9'] > df['EMA21']) & (df['EMA9'].shift(1) <= df['EMA21'].shift(1)), 1,
            np.where(
                (df['EMA9'] < df['EMA21']) & (df['EMA9'].shift(1) >= df['EMA21'].shift(1)), -1, 0
            )
        )
        
        return df
    
    def _compute_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
        """Compute Bollinger Bands."""
        sma = df['close'].rolling(window=period).mean()
        rolling_std = df['close'].rolling(window=period).std()
        
        df['BB_Upper'] = sma + (rolling_std * std)
        df['BB_Lower'] = sma - (rolling_std * std)
        df['BB_Middle'] = sma
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
        df['BB_Position'] = (df['close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        return df
    
    def _compute_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Compute ATR (Average True Range)."""
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = true_range.rolling(window=period).mean()
        df['ATR_Pct'] = df['ATR'] / df['close'] * 100
        
        return df
    
    def _compute_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Compute ADX (Average Directional Index)."""
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift()).abs(),
            (df['low'] - df['close'].shift()).abs()
        ], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr.replace(0, np.inf))
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr.replace(0, np.inf))
        
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.inf)
        df['ADX'] = dx.rolling(window=period).mean()
        df['Plus_DI'] = plus_di
        df['Minus_DI'] = minus_di
        
        return df
    
    def _compute_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute VWAP (Volume Weighted Average Price)."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        cumulative_tp_vol = (typical_price * df['volume']).cumsum()
        cumulative_vol = df['volume'].cumsum()
        
        df['VWAP'] = cumulative_tp_vol / cumulative_vol.replace(0, np.inf)
        df['VWAP_Diff'] = (df['close'] - df['VWAP']) / df['VWAP'] * 100
        
        return df
    
    def _compute_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute volume-related features."""
        df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['volume'] / df['Volume_MA20'].replace(0, np.inf)
        df['Volume_Spike'] = (df['Volume_Ratio'] > 1.5).astype(int)
        
        # On-Balance Volume
        obv = (np.sign(df['close'].diff()) * df['volume']).cumsum()
        df['OBV'] = obv
        df['OBV_MA'] = obv.rolling(window=20).mean()
        
        return df
    
    def _compute_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute trend-related derived features."""
        # Trend strength using ADX + DI
        if 'ADX' in df.columns and 'Plus_DI' in df.columns and 'Minus_DI' in df.columns:
            df['Trend_Strength'] = df['ADX'].clip(0, 100)
            df['Trend_Direction'] = np.where(
                df['Plus_DI'] > df['Minus_DI'], 1, -1
            )
        
        # Price relative to moving averages
        if 'EMA9' in df.columns and 'EMA21' in df.columns:
            df['Price_Above_EMA9'] = (df['close'] > df['EMA9']).astype(int)
            df['Price_Above_EMA21'] = (df['close'] > df['EMA21']).astype(int)
        
        # Higher highs / lower lows
        df['Higher_High'] = (df['high'] > df['high'].shift(1)).astype(int)
        df['Lower_Low'] = (df['low'] < df['low'].shift(1)).astype(int)
        
        return df
    
    def _compute_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute momentum features."""
        # Rate of Change
        df['ROC_5'] = df['close'].pct_change(5) * 100
        df['ROC_10'] = df['close'].pct_change(10) * 100
        
        # Stochastic
        low_14 = df['low'].rolling(14).min()
        high_14 = df['high'].rolling(14).max()
        df['Stoch_K'] = 100 * (df['close'] - low_14) / (high_14 - low_14).replace(0, np.inf)
        df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()
        
        return df
    
    def _compute_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute candlestick pattern features."""
        body = abs(df['close'] - df['open'])
        upper_shadow = df['high'] - df[['close', 'open']].max(axis=1)
        lower_shadow = df[['close', 'open']].min(axis=1) - df['low']
        total_range = df['high'] - df['low']
        
        # Doji
        df['Is_Doji'] = (body / total_range.replace(0, np.inf) < 0.1).astype(int)
        
        # Hammer
        df['Is_Hammer'] = (
            (lower_shadow > 2 * body) & 
            (upper_shadow < body * 0.5) &
            (df['close'] > df['open'])
        ).astype(int)
        
        # Shooting Star
        df['Is_ShootingStar'] = (
            (upper_shadow > 2 * body) & 
            (lower_shadow < body * 0.5) &
            (df['close'] < df['open'])
        ).astype(int)
        
        # Engulfing
        df['Bullish_Engulfing'] = (
            (df['close'] > df['open']) &
            (df['close'].shift(1) < df['open'].shift(1)) &
            (df['close'] > df['open'].shift(1)) &
            (df['open'] < df['close'].shift(1))
        ).astype(int)
        
        df['Bearish_Engulfing'] = (
            (df['close'] < df['open']) &
            (df['close'].shift(1) > df['open'].shift(1)) &
            (df['close'] < df['open'].shift(1)) &
            (df['open'] > df['close'].shift(1))
        ).astype(int)
        
        return df
    
    def get_feature_vector(self, df: pd.DataFrame, feature_names: List[str]) -> pd.DataFrame:
        """Extract specific features as a feature vector for ML models."""
        available = [f for f in feature_names if f in df.columns]
        missing = [f for f in feature_names if f not in df.columns]
        
        if missing:
            logger.warning(f"Missing features: {missing}")
        
        return df[available].copy()
    
    def get_latest_features(self, symbol: str) -> Optional[Dict]:
        """Get the latest feature values for a symbol."""
        if symbol in self._feature_cache and not self._feature_cache[symbol].empty:
            return self._feature_cache[symbol].iloc[-1].to_dict()
        return None
