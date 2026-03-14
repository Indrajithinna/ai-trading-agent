"""
Signal Aggregator Agent (Module 9), Trade Scoring Engine (Module 10),
Smart Strike Selector (Module 11)
=====================================================================
Collects signals from multiple strategies, computes consensus,
scores trades, and selects optimal strike prices.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from ai_trading_agent.strategies.base_strategy import StrategySignal, SignalType
from ai_trading_agent.agents.regime_detector import RegimeInfo, MarketRegime
from ai_trading_agent.agents.multi_timeframe_engine import MTFResult, TimeframeBias
from ai_trading_agent.config import TradingConfig
from ai_trading_agent.utils.helpers import get_atm_strike, get_strike_interval, round_to_tick
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("SignalAggregator")


@dataclass
class AggregatedSignal:
    """Final aggregated signal with all scoring and strike selection."""
    signal_id: str
    symbol: str
    direction: str  # "BUY_CALL" or "BUY_PUT"
    strike: int
    option_type: str  # "CE" or "PE"
    entry_price: float
    target1: float
    target2: float
    stop_loss: float
    
    # Scoring
    trade_score: float
    ai_confidence: float
    
    # Consensus
    confirming_agents: int
    total_agents: int
    confirming_names: List[str]
    
    # Context
    market_regime: str
    mtf_aligned: bool
    spot_price: float
    
    # Meta
    timestamp: datetime = field(default_factory=datetime.now)
    executed: bool = False
    result: str = ""


class SignalAggregator:
    """
    Module 9: Collects signals from all strategy agents.
    Consensus rule: 3 or more agents agree → allow trade.
    """
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self._signals_buffer: Dict[str, List[StrategySignal]] = {}
        logger.info("SignalAggregator initialized")
    
    def aggregate(self, signals: List[StrategySignal], symbol: str) -> Optional[Dict]:
        """
        Aggregate signals from multiple strategies.
        
        Args:
            signals: List of signals from all strategy agents
            symbol: Trading symbol
            
        Returns:
            Aggregation result with consensus data, or None if no consensus
        """
        # Filter actionable signals
        actionable = [s for s in signals if s.is_actionable]
        
        if not actionable:
            return None
        
        # Count by direction
        call_signals = [s for s in actionable if s.signal_type == SignalType.BUY_CALL]
        put_signals = [s for s in actionable if s.signal_type == SignalType.BUY_PUT]
        
        # Determine majority direction
        if len(call_signals) >= len(put_signals):
            majority = call_signals
            direction = "BUY_CALL"
        else:
            majority = put_signals
            direction = "BUY_PUT"
        
        # Check consensus
        confirming_count = len(majority)
        total_agents = len(signals)
        
        consensus_met = confirming_count >= self.config.min_consensus_agents
        
        # Average confidence
        avg_confidence = np.mean([s.confidence for s in majority]) if majority else 0
        
        # Average entry, targets, SL
        avg_entry = np.mean([s.entry_price for s in majority if s.entry_price > 0])
        avg_target1 = np.mean([s.target1 for s in majority if s.target1 > 0])
        avg_target2 = np.mean([s.target2 for s in majority if s.target2 > 0])
        avg_sl = np.mean([s.stop_loss for s in majority if s.stop_loss > 0])
        
        result = {
            "symbol": symbol,
            "direction": direction,
            "consensus_met": consensus_met,
            "confirming_count": confirming_count,
            "total_agents": total_agents,
            "confirming_strategies": [s.strategy_name for s in majority],
            "avg_confidence": round(avg_confidence, 2),
            "avg_entry": round(avg_entry, 2) if not np.isnan(avg_entry) else 0,
            "avg_target1": round(avg_target1, 2) if not np.isnan(avg_target1) else 0,
            "avg_target2": round(avg_target2, 2) if not np.isnan(avg_target2) else 0,
            "avg_sl": round(avg_sl, 2) if not np.isnan(avg_sl) else 0,
            "all_signals": signals
        }
        
        status = "✅ CONSENSUS" if consensus_met else "❌ NO CONSENSUS"
        logger.info(
            f"📡 {symbol} {status}: {confirming_count}/{total_agents} agents → {direction} | "
            f"Avg Confidence: {avg_confidence:.0f}%"
        )
        
        return result


class TradeScoreEngine:
    """
    Module 10: Computes a composite trade score using multiple factors.
    Execute trade only if score ≥ 70.
    """
    
    WEIGHTS = {
        "trend_strength": 0.15,
        "vwap_alignment": 0.12,
        "rsi_signal": 0.12,
        "volume_spike": 0.10,
        "ai_prediction": 0.18,
        "market_regime": 0.10,
        "mtf_confirmation": 0.13,
        "agent_consensus": 0.10
    }
    
    def __init__(self, config: TradingConfig):
        self.config = config
        logger.info("TradeScoreEngine initialized")
    
    def compute_score(self, 
                      aggregation: Dict,
                      regime_info: Optional[RegimeInfo] = None,
                      mtf_result: Optional[MTFResult] = None,
                      ai_prediction: Optional[Dict] = None,
                      features: Optional[Dict] = None) -> float:
        """
        Compute composite trade score (0-100).
        
        Components:
        1. Trend strength (ADX-based)
        2. VWAP alignment
        3. RSI signal quality
        4. Volume spike detection
        5. AI prediction confidence
        6. Market regime favorability
        7. Multi-timeframe confirmation
        8. Agent consensus strength
        """
        scores = {}
        
        # 1. Trend Strength (from features)
        if features and 'Trend_Strength' in features:
            scores['trend_strength'] = min(100, features['Trend_Strength'] * 2)
        elif features and 'ADX' in features:
            scores['trend_strength'] = min(100, features['ADX'] * 2)
        else:
            scores['trend_strength'] = 40
        
        # 2. VWAP Alignment
        if features and 'VWAP_Diff' in features:
            vwap_diff = abs(features['VWAP_Diff'])
            direction = aggregation.get('direction', '')
            
            if direction == 'BUY_CALL' and features['VWAP_Diff'] > 0:
                scores['vwap_alignment'] = min(100, 50 + vwap_diff * 100)
            elif direction == 'BUY_PUT' and features['VWAP_Diff'] < 0:
                scores['vwap_alignment'] = min(100, 50 + vwap_diff * 100)
            else:
                scores['vwap_alignment'] = max(0, 30 - vwap_diff * 50)
        else:
            scores['vwap_alignment'] = 50
        
        # 3. RSI Signal
        if features and 'RSI' in features:
            rsi = features['RSI']
            direction = aggregation.get('direction', '')
            if direction == 'BUY_CALL':
                scores['rsi_signal'] = min(100, max(0, (rsi - 40) * 2.5))
            else:
                scores['rsi_signal'] = min(100, max(0, (60 - rsi) * 2.5))
        else:
            scores['rsi_signal'] = 50
        
        # 4. Volume Spike
        if features and 'Volume_Ratio' in features:
            vol_ratio = features['Volume_Ratio']
            if vol_ratio > 2.0:
                scores['volume_spike'] = 100
            elif vol_ratio > 1.5:
                scores['volume_spike'] = 75
            elif vol_ratio > 1.0:
                scores['volume_spike'] = 50
            else:
                scores['volume_spike'] = 25
        else:
            scores['volume_spike'] = 50
        
        # 5. AI Prediction Confidence
        if ai_prediction:
            pred_direction = ai_prediction.get('prediction', 'HOLD')
            agg_direction = aggregation.get('direction', '')
            ai_conf = ai_prediction.get('confidence', 50)
            
            if pred_direction == agg_direction:
                scores['ai_prediction'] = min(100, ai_conf)
            elif pred_direction == 'HOLD':
                scores['ai_prediction'] = 30
            else:
                scores['ai_prediction'] = max(0, 20 - ai_conf * 0.2)
        else:
            scores['ai_prediction'] = 50
        
        # 6. Market Regime
        if regime_info:
            if regime_info.regime == MarketRegime.TRENDING:
                scores['market_regime'] = 85
            elif regime_info.regime == MarketRegime.SIDEWAYS:
                scores['market_regime'] = 45
            elif regime_info.regime == MarketRegime.VOLATILE:
                scores['market_regime'] = 60
            else:
                scores['market_regime'] = 50
        else:
            scores['market_regime'] = 50
        
        # 7. Multi-Timeframe Confirmation
        if mtf_result:
            if mtf_result.aligned and mtf_result.trade_allowed:
                scores['mtf_confirmation'] = min(100, mtf_result.confidence)
            elif mtf_result.aligned:
                scores['mtf_confirmation'] = 60
            else:
                scores['mtf_confirmation'] = 20
        else:
            scores['mtf_confirmation'] = 50
        
        # 8. Agent Consensus
        confirming = aggregation.get('confirming_count', 0)
        total = aggregation.get('total_agents', 1)
        consensus_pct = (confirming / total * 100) if total > 0 else 0
        scores['agent_consensus'] = min(100, consensus_pct * 1.2)
        
        # Weighted composite score
        composite = sum(
            scores.get(k, 50) * w 
            for k, w in self.WEIGHTS.items()
        )
        
        logger.info(
            f"📊 Trade Score: {composite:.1f}/100 | "
            f"Components: {', '.join(f'{k}={v:.0f}' for k, v in scores.items())}"
        )
        
        return round(composite, 2)


class SmartStrikeSelector:
    """
    Module 11: Automatically selects optimal strike price.
    
    ATM → moderate confidence
    OTM → strong confidence (higher risk/reward)
    ITM → weak confidence (safer, lower reward)
    """
    
    def __init__(self, config: TradingConfig):
        self.config = config
        logger.info("SmartStrikeSelector initialized")
    
    def select_strike(self, symbol: str, spot_price: float, 
                      direction: str, confidence: float,
                      option_chain: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Select optimal strike price based on confidence and market data.
        
        Args:
            symbol: Trading symbol
            spot_price: Current spot price
            direction: "BUY_CALL" or "BUY_PUT"
            confidence: Trade confidence score (0-100)
            option_chain: Optional option chain data
            
        Returns:
            Strike selection details with entry, targets, and stop loss
        """
        interval = get_strike_interval(symbol)
        atm = get_atm_strike(spot_price, symbol)
        
        # Determine strike offset based on confidence
        if confidence >= 80:
            # Strong confidence → OTM (higher risk/reward)
            offset = 1  # 1 strike OTM
            strike_type = "OTM"
        elif confidence >= 60:
            # Moderate confidence → ATM
            offset = 0
            strike_type = "ATM"
        else:
            # Weak confidence → ITM (safer)
            offset = -1  # 1 strike ITM
            strike_type = "ITM"
        
        # Calculate strike based on direction
        if direction == "BUY_CALL":
            strike = atm + (offset * interval)
            option_type = "CE"
        else:  # BUY_PUT
            strike = atm - (offset * interval)
            option_type = "PE"
        
        # Estimate option price
        option_price = self._estimate_option_price(
            spot_price, strike, direction, option_chain
        )
        
        # Calculate entry, targets, stop loss
        entry_price = round_to_tick(option_price)
        
        # Target and SL based on option price
        sl_pct = 0.25  # 25% SL
        target1_pct = 0.25  # 25% target1
        target2_pct = 0.50  # 50% target2
        
        stop_loss = round_to_tick(entry_price * (1 - sl_pct))
        target1 = round_to_tick(entry_price * (1 + target1_pct))
        target2 = round_to_tick(entry_price * (1 + target2_pct))
        
        result = {
            "symbol": symbol,
            "strike": strike,
            "option_type": option_type,
            "strike_type": strike_type,
            "atm_strike": atm,
            "spot_price": round(spot_price, 2),
            "entry_price": entry_price,
            "target1": target1,
            "target2": target2,
            "stop_loss": stop_loss,
            "estimated_premium": entry_price,
            "risk_reward_t1": round((target1 - entry_price) / (entry_price - stop_loss), 2) 
                if (entry_price - stop_loss) > 0 else 0,
            "risk_reward_t2": round((target2 - entry_price) / (entry_price - stop_loss), 2)
                if (entry_price - stop_loss) > 0 else 0,
        }
        
        logger.info(
            f"🎯 {symbol} {strike} {option_type} ({strike_type}) | "
            f"Entry: {entry_price} | T1: {target1} | T2: {target2} | SL: {stop_loss}"
        )
        
        return result
    
    def _estimate_option_price(self, spot: float, strike: int, 
                               direction: str, 
                               option_chain: Optional[pd.DataFrame] = None) -> float:
        """Estimate option premium from chain or approximation."""
        # Try to get from option chain
        if option_chain is not None and not option_chain.empty:
            col = 'ce_ltp' if direction == "BUY_CALL" else 'pe_ltp'
            if 'strike' in option_chain.columns and col in option_chain.columns:
                row = option_chain[option_chain['strike'] == strike]
                if not row.empty:
                    return float(row[col].iloc[0])
        
        # Approximate pricing
        moneyness = abs(spot - strike)
        intrinsic = max(0, spot - strike) if direction == "BUY_CALL" else max(0, strike - spot)
        time_value = max(10, 50 - moneyness * 0.1)  # Simplified
        
        return max(5, round(intrinsic + time_value, 2))
