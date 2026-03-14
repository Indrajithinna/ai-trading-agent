"""
Performance Analyzer (Module 15)
==================================
Tracks: total trades, win rate, daily P&L, max drawdown, risk metrics.
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from collections import defaultdict

import numpy as np

from ai_trading_agent.utils.helpers import format_currency, get_ist_now
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("PerformanceAnalyzer")


class PerformanceAnalyzer:
    """
    Comprehensive trading performance tracking and analysis.
    
    Metrics:
    - Total trades, win rate, profit factor
    - Daily P&L tracking
    - Maximum drawdown
    - Sharpe ratio, Sortino ratio
    - Average win/loss, expectancy
    - Strategy-level performance
    - Risk-adjusted metrics
    """
    
    def __init__(self):
        self._trades: List[Dict] = []
        self._daily_pnl: Dict[str, float] = {}
        self._equity_curve: List[float] = [0]
        self._peak_equity: float = 0
        self._strategy_performance: Dict[str, List[Dict]] = defaultdict(list)
        
        # Data directory
        self._data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(self._data_dir, exist_ok=True)
        
        logger.info("PerformanceAnalyzer initialized")
    
    def record_trade(self, trade: Dict[str, Any]):
        """Record a completed trade for analysis."""
        self._trades.append({
            **trade,
            'recorded_at': datetime.now().isoformat()
        })
        
        # Update daily P&L
        trade_date = str(date.today())
        pnl = trade.get('pnl', 0)
        self._daily_pnl[trade_date] = self._daily_pnl.get(trade_date, 0) + pnl
        
        # Update equity curve
        self._equity_curve.append(self._equity_curve[-1] + pnl)
        
        # Peak equity tracking
        if self._equity_curve[-1] > self._peak_equity:
            self._peak_equity = self._equity_curve[-1]
        
        # Strategy tracking
        strategy = trade.get('strategy', 'unknown')
        self._strategy_performance[strategy].append(trade)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        if not self._trades:
            return self._empty_summary()
        
        pnl_list = [t.get('pnl', 0) for t in self._trades]
        wins = [p for p in pnl_list if p > 0]
        losses = [p for p in pnl_list if p < 0]
        
        total_trades = len(self._trades)
        winning_trades = len(wins)
        losing_trades = len(losses)
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = sum(pnl_list)
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        # Profit factor
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        # Max drawdown
        max_drawdown = self._calculate_max_drawdown()
        
        # Sharpe ratio (daily returns)
        sharpe = self._calculate_sharpe_ratio()
        
        # Sortino ratio
        sortino = self._calculate_sortino_ratio()
        
        # Expectancy
        if total_trades > 0:
            expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)
        else:
            expectancy = 0
        
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "largest_win": round(max(wins) if wins else 0, 2),
            "largest_loss": round(min(losses) if losses else 0, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "expectancy": round(expectancy, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "avg_trade": round(total_pnl / total_trades, 2) if total_trades > 0 else 0,
            "consecutive_wins": self._max_consecutive(True),
            "consecutive_losses": self._max_consecutive(False),
            "daily_pnl_history": dict(sorted(self._daily_pnl.items())),
            "equity_curve": self._equity_curve[-100:],  # Last 100 points
        }
    
    def get_strategy_breakdown(self) -> Dict[str, Dict]:
        """Get performance breakdown by strategy."""
        result = {}
        
        for strategy, trades in self._strategy_performance.items():
            pnl_list = [t.get('pnl', 0) for t in trades]
            wins = [p for p in pnl_list if p > 0]
            
            result[strategy] = {
                "total_trades": len(trades),
                "winning_trades": len(wins),
                "win_rate": round(len(wins) / len(trades) * 100, 2) if trades else 0,
                "total_pnl": round(sum(pnl_list), 2),
                "avg_pnl": round(np.mean(pnl_list), 2) if pnl_list else 0,
            }
        
        return result
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from equity curve."""
        if len(self._equity_curve) < 2:
            return 0
        
        peak = self._equity_curve[0]
        max_dd = 0
        
        for value in self._equity_curve:
            if value > peak:
                peak = value
            dd = peak - value
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.06) -> float:
        """Calculate Sharpe ratio from daily returns."""
        if len(self._daily_pnl) < 2:
            return 0
        
        returns = list(self._daily_pnl.values())
        if not returns:
            return 0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0
        
        # Annualized (250 trading days)
        daily_rf = risk_free_rate / 250
        sharpe = (mean_return - daily_rf) / std_return * np.sqrt(250)
        
        return sharpe
    
    def _calculate_sortino_ratio(self, risk_free_rate: float = 0.06) -> float:
        """Calculate Sortino ratio (penalizes only downside volatility)."""
        if len(self._daily_pnl) < 2:
            return 0
        
        returns = list(self._daily_pnl.values())
        mean_return = np.mean(returns)
        
        downside_returns = [r for r in returns if r < 0]
        if not downside_returns:
            return float('inf') if mean_return > 0 else 0
        
        downside_std = np.std(downside_returns)
        if downside_std == 0:
            return 0
        
        daily_rf = risk_free_rate / 250
        sortino = (mean_return - daily_rf) / downside_std * np.sqrt(250)
        
        return sortino
    
    def _max_consecutive(self, wins: bool) -> int:
        """Calculate max consecutive wins or losses."""
        max_streak = 0
        current_streak = 0
        
        for trade in self._trades:
            pnl = trade.get('pnl', 0)
            if (wins and pnl > 0) or (not wins and pnl < 0):
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary when no trades exist."""
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "max_drawdown": 0,
            "sharpe_ratio": 0,
            "sortino_ratio": 0,
            "expectancy": 0,
        }
    
    def save_report(self):
        """Save performance report to disk."""
        report = self.get_summary()
        report['strategy_breakdown'] = self.get_strategy_breakdown()
        report['generated_at'] = datetime.now().isoformat()
        
        path = os.path.join(self._data_dir, f"performance_{date.today()}.json")
        with open(path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📊 Performance report saved: {path}")
    
    def load_trades(self, filepath: str = ""):
        """Load historical trades from a file."""
        if not filepath:
            filepath = os.path.join(self._data_dir, "trade_history.json")
        
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    trades = json.load(f)
                for trade in trades:
                    self.record_trade(trade)
                logger.info(f"📂 Loaded {len(trades)} historical trades")
        except Exception as e:
            logger.error(f"Error loading trades: {e}")
