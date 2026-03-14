"""
Market Scanner Agent (Module 2)
================================
Scans all configured markets for trading opportunities.
Identifies high-momentum moves, volume spikes, and breakout setups.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

from ai_trading_agent.config import MarketConfig, StrategyConfig
from ai_trading_agent.agents.market_data_agent import MarketDataAgent
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("ScannerAgent")


@dataclass
class ScanResult:
    """Result of a market scan."""
    symbol: str
    scan_type: str  # "momentum", "volume_spike", "breakout", "reversal"
    strength: float  # 0-100
    direction: str  # "BULLISH", "BEARISH", "NEUTRAL"
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class MarketScannerAgent:
    """
    Scans markets for trading opportunities.
    
    Scan Types:
    - Momentum Scanner: Identifies strong directional moves
    - Volume Scanner: Detects unusual volume activity
    - Breakout Scanner: Finds price breakout patterns
    - Reversal Scanner: Spots potential reversal setups
    """
    
    def __init__(self, market_data: MarketDataAgent, config: StrategyConfig):
        self.market_data = market_data
        self.config = config
        self._scan_results: Dict[str, List[ScanResult]] = {}
        logger.info("MarketScannerAgent initialized")
    
    def scan_all_markets(self, symbols: List[str]) -> Dict[str, List[ScanResult]]:
        """Run all scanners across all configured markets."""
        all_results = {}
        
        for symbol in symbols:
            results = []
            
            # Get data for analysis
            df_15m = self.market_data.get_ohlc_data(symbol, 15, 50)
            df_5m = self.market_data.get_ohlc_data(symbol, 5, 100)
            df_1m = self.market_data.get_ohlc_data(symbol, 1, 100)
            
            if df_15m.empty or df_5m.empty:
                continue
            
            # Run scanners
            momentum = self._scan_momentum(symbol, df_5m)
            if momentum:
                results.append(momentum)
            
            volume = self._scan_volume(symbol, df_5m)
            if volume:
                results.append(volume)
            
            breakout = self._scan_breakout(symbol, df_15m, df_5m)
            if breakout:
                results.append(breakout)
            
            reversal = self._scan_reversal(symbol, df_5m)
            if reversal:
                results.append(reversal)
            
            all_results[symbol] = results
            self._scan_results[symbol] = results
        
        active_signals = sum(len(v) for v in all_results.values())
        logger.info(f"🔍 Market scan complete. {active_signals} opportunities found across {len(symbols)} markets")
        
        return all_results
    
    def _scan_momentum(self, symbol: str, df: pd.DataFrame) -> Optional[ScanResult]:
        """Scan for momentum signals using RSI and price action."""
        if len(df) < 20:
            return None
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        price_change_pct = ((df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]) * 100
        
        strength = 0
        direction = "NEUTRAL"
        
        if current_rsi > 60 and price_change_pct > 0.1:
            strength = min(100, (current_rsi - 50) * 2 + price_change_pct * 10)
            direction = "BULLISH"
        elif current_rsi < 40 and price_change_pct < -0.1:
            strength = min(100, (50 - current_rsi) * 2 + abs(price_change_pct) * 10)
            direction = "BEARISH"
        
        if strength > 30:
            return ScanResult(
                symbol=symbol,
                scan_type="momentum",
                strength=round(strength, 2),
                direction=direction,
                details={
                    "rsi": round(current_rsi, 2),
                    "price_change_pct": round(price_change_pct, 4),
                    "last_price": round(df['close'].iloc[-1], 2)
                }
            )
        return None
    
    def _scan_volume(self, symbol: str, df: pd.DataFrame) -> Optional[ScanResult]:
        """Scan for unusual volume activity."""
        if len(df) < 25:
            return None
        
        vol_ma = df['volume'].rolling(window=20).mean()
        current_vol = df['volume'].iloc[-1]
        avg_vol = vol_ma.iloc[-1]
        
        if avg_vol == 0:
            return None
        
        volume_ratio = current_vol / avg_vol
        price_change = df['close'].iloc[-1] - df['close'].iloc[-2]
        
        if volume_ratio > self.config.vwap_volume_spike_multiplier:
            strength = min(100, volume_ratio * 25)
            direction = "BULLISH" if price_change > 0 else "BEARISH"
            
            return ScanResult(
                symbol=symbol,
                scan_type="volume_spike",
                strength=round(strength, 2),
                direction=direction,
                details={
                    "volume_ratio": round(volume_ratio, 2),
                    "current_volume": int(current_vol),
                    "avg_volume": int(avg_vol),
                    "price_change": round(price_change, 2)
                }
            )
        return None
    
    def _scan_breakout(self, symbol: str, df_15m: pd.DataFrame, df_5m: pd.DataFrame) -> Optional[ScanResult]:
        """Scan for price breakouts from consolidation zones."""
        if len(df_15m) < 20:
            return None
        
        # Calculate consolidation range (last 10 bars of 15m)
        recent = df_15m.tail(10)
        range_high = recent['high'].max()
        range_low = recent['low'].min()
        range_width = (range_high - range_low) / range_low * 100
        
        current_price = df_5m['close'].iloc[-1] if not df_5m.empty else df_15m['close'].iloc[-1]
        
        # Check for breakout
        if range_width < 1.0:  # Tight consolidation
            if current_price > range_high:
                strength = min(100, ((current_price - range_high) / range_high * 10000) + 50)
                return ScanResult(
                    symbol=symbol,
                    scan_type="breakout",
                    strength=round(strength, 2),
                    direction="BULLISH",
                    details={
                        "range_high": round(range_high, 2),
                        "range_low": round(range_low, 2),
                        "breakout_price": round(current_price, 2),
                        "range_width_pct": round(range_width, 4)
                    }
                )
            elif current_price < range_low:
                strength = min(100, ((range_low - current_price) / range_low * 10000) + 50)
                return ScanResult(
                    symbol=symbol,
                    scan_type="breakout",
                    strength=round(strength, 2),
                    direction="BEARISH",
                    details={
                        "range_high": round(range_high, 2),
                        "range_low": round(range_low, 2),
                        "breakout_price": round(current_price, 2),
                        "range_width_pct": round(range_width, 4)
                    }
                )
        return None
    
    def _scan_reversal(self, symbol: str, df: pd.DataFrame) -> Optional[ScanResult]:
        """Scan for potential reversal setups."""
        if len(df) < 30:
            return None
        
        # RSI divergence check
        delta = df['close'].diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        price_trend = df['close'].iloc[-1] - df['close'].iloc[-10]
        rsi_trend = rsi.iloc[-1] - rsi.iloc[-10]
        
        # Bearish divergence: price up, RSI down
        if price_trend > 0 and rsi_trend < 0 and current_rsi > 70:
            return ScanResult(
                symbol=symbol,
                scan_type="reversal",
                strength=round(min(100, current_rsi), 2),
                direction="BEARISH",
                details={
                    "type": "bearish_divergence",
                    "rsi": round(current_rsi, 2),
                    "price_trend": round(price_trend, 2),
                    "rsi_trend": round(rsi_trend, 2)
                }
            )
        
        # Bullish divergence: price down, RSI up
        if price_trend < 0 and rsi_trend > 0 and current_rsi < 30:
            return ScanResult(
                symbol=symbol,
                scan_type="reversal",
                strength=round(min(100, 100 - current_rsi), 2),
                direction="BULLISH",
                details={
                    "type": "bullish_divergence",
                    "rsi": round(current_rsi, 2),
                    "price_trend": round(price_trend, 2),
                    "rsi_trend": round(rsi_trend, 2)
                }
            )
        
        return None
    
    def get_top_opportunities(self, n: int = 5) -> List[ScanResult]:
        """Get the top N trading opportunities across all markets."""
        all_results = []
        for results in self._scan_results.values():
            all_results.extend(results)
        
        # Sort by strength descending
        all_results.sort(key=lambda x: x.strength, reverse=True)
        return all_results[:n]
