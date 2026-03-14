"""
Risk Management Engine (Module 12)
====================================
Enforces all risk limits: capital, daily loss, profit target, trade count.
Stops trading when any limit is reached.
"""

from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime, date

from ai_trading_agent.config import TradingConfig
from ai_trading_agent.utils.helpers import format_currency
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("RiskManager")


@dataclass
class DailyRiskState:
    """Daily risk tracking state."""
    date: date = field(default_factory=date.today)
    starting_capital: float = 0.0
    current_capital: float = 0.0
    daily_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    max_drawdown: float = 0.0
    peak_capital: float = 0.0
    is_trading_allowed: bool = True
    stop_reason: str = ""


class RiskManager:
    """
    Enforces risk management rules for the trading system.
    
    Rules:
    - Capital: ₹8,000
    - Max daily loss: ₹400
    - Daily profit target: ₹600
    - Max trades per day: 10
    - Risk per trade: 1-2%
    
    Stops trading when:
    - Daily loss >= ₹400
    - Daily profit >= ₹600
    - Trades >= 10
    """
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.state = DailyRiskState(
            starting_capital=config.initial_capital,
            current_capital=config.initial_capital,
            peak_capital=config.initial_capital
        )
        self._trade_history: List[Dict] = []
        logger.info(
            f"RiskManager initialized | Capital: {format_currency(config.initial_capital)} | "
            f"Max Loss: {format_currency(config.max_daily_loss)} | "
            f"Target: {format_currency(config.daily_profit_target)}"
        )
    
    def check_trade_allowed(self) -> Dict[str, Any]:
        """
        Check if a new trade is allowed based on all risk parameters.
        
        Returns:
            Dictionary with 'allowed' flag and reason
        """
        # Check daily date reset
        if self.state.date != date.today():
            self._reset_daily()
        
        reasons = []
        
        # Check daily loss limit
        if self.state.daily_pnl <= -self.config.max_daily_loss:
            reasons.append(f"Daily loss limit reached ({format_currency(self.state.daily_pnl)})")
        
        # Check profit target
        if self.state.daily_pnl >= self.config.daily_profit_target:
            reasons.append(f"Daily profit target reached ({format_currency(self.state.daily_pnl)})")
        
        # Check trade count
        if self.state.total_trades >= self.config.max_trades_per_day:
            reasons.append(f"Max trades reached ({self.state.total_trades}/{self.config.max_trades_per_day})")
        
        allowed = len(reasons) == 0
        
        if not allowed:
            self.state.is_trading_allowed = False
            self.state.stop_reason = "; ".join(reasons)
            logger.warning(f"🚫 Trading STOPPED: {self.state.stop_reason}")
        
        return {
            "allowed": allowed,
            "reasons": reasons,
            "daily_pnl": self.state.daily_pnl,
            "trades_remaining": max(0, self.config.max_trades_per_day - self.state.total_trades),
            "loss_remaining": round(self.config.max_daily_loss + self.state.daily_pnl, 2),
            "profit_remaining": round(self.config.daily_profit_target - self.state.daily_pnl, 2)  
        }
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> Dict[str, Any]:
        """
        Calculate position size based on risk per trade.
        
        Args:
            entry_price: Entry price of the option
            stop_loss: Stop loss price
            
        Returns:
            Position sizing details
        """
        risk_amount_min = self.state.current_capital * self.config.risk_per_trade_min
        risk_amount_max = self.state.current_capital * self.config.risk_per_trade_max
        
        # Risk per unit
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit <= 0:
            return {
                "quantity": 0,
                "risk_amount": 0,
                "reason": "Invalid stop loss"
            }
        
        # Calculate quantity
        min_qty = max(1, int(risk_amount_min / risk_per_unit))
        max_qty = max(1, int(risk_amount_max / risk_per_unit))
        
        # Use conservative quantity
        quantity = min_qty
        
        # Ensure trade doesn't exceed remaining loss budget
        remaining_loss = self.config.max_daily_loss + self.state.daily_pnl
        max_loss_qty = max(1, int(remaining_loss / risk_per_unit))
        quantity = min(quantity, max_loss_qty)
        
        # Ensure capital covers the trade
        trade_cost = entry_price * quantity
        if trade_cost > self.state.current_capital * 0.5:  # Max 50% of capital per trade
            quantity = max(1, int(self.state.current_capital * 0.5 / entry_price))
        
        actual_risk = quantity * risk_per_unit
        
        return {
            "quantity": quantity,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "risk_per_unit": round(risk_per_unit, 2),
            "total_risk": round(actual_risk, 2),
            "risk_pct": round(actual_risk / self.state.current_capital * 100, 2),
            "trade_cost": round(entry_price * quantity, 2),
            "capital_used_pct": round(entry_price * quantity / self.state.current_capital * 100, 2)
        }
    
    def record_trade(self, trade: Dict[str, Any]):
        """
        Record a completed trade and update risk state.
        
        Args:
            trade: Dictionary with trade details including P&L
        """
        pnl = trade.get('pnl', 0)
        
        self.state.total_trades += 1
        self.state.daily_pnl += pnl
        self.state.current_capital += pnl
        
        if pnl > 0:
            self.state.winning_trades += 1
        elif pnl < 0:
            self.state.losing_trades += 1
        
        # Update peak and drawdown
        if self.state.current_capital > self.state.peak_capital:
            self.state.peak_capital = self.state.current_capital
        
        current_drawdown = self.state.peak_capital - self.state.current_capital
        if current_drawdown > self.state.max_drawdown:
            self.state.max_drawdown = current_drawdown
        
        self._trade_history.append({
            **trade,
            "trade_number": self.state.total_trades,
            "cumulative_pnl": self.state.daily_pnl,
            "capital": self.state.current_capital,
            "timestamp": datetime.now().isoformat()
        })
        
        win_rate = (self.state.winning_trades / self.state.total_trades * 100) \
            if self.state.total_trades > 0 else 0
        
        logger.info(
            f"📝 Trade #{self.state.total_trades} | P&L: {format_currency(pnl)} | "
            f"Daily P&L: {format_currency(self.state.daily_pnl)} | "
            f"Win Rate: {win_rate:.0f}% | Capital: {format_currency(self.state.current_capital)}"
        )
    
    def _reset_daily(self):
        """Reset daily tracking for a new trading day."""
        logger.info("🔄 Daily risk state reset")
        self.state = DailyRiskState(
            date=date.today(),
            starting_capital=self.state.current_capital,
            current_capital=self.state.current_capital,
            peak_capital=self.state.current_capital
        )
        self._trade_history = []
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get comprehensive risk status."""
        win_rate = (self.state.winning_trades / self.state.total_trades * 100) \
            if self.state.total_trades > 0 else 0
        
        return {
            "date": str(self.state.date),
            "capital": round(self.state.current_capital, 2),
            "starting_capital": round(self.state.starting_capital, 2),
            "daily_pnl": round(self.state.daily_pnl, 2),
            "daily_pnl_pct": round(self.state.daily_pnl / self.state.starting_capital * 100, 2),
            "total_trades": self.state.total_trades,
            "winning_trades": self.state.winning_trades,
            "losing_trades": self.state.losing_trades,
            "win_rate": round(win_rate, 2),
            "max_drawdown": round(self.state.max_drawdown, 2),
            "is_trading_allowed": self.state.is_trading_allowed,
            "stop_reason": self.state.stop_reason,
            "trades_remaining": max(0, self.config.max_trades_per_day - self.state.total_trades),
            "loss_budget_remaining": round(self.config.max_daily_loss + self.state.daily_pnl, 2),
            "profit_target_remaining": round(self.config.daily_profit_target - self.state.daily_pnl, 2)
        }
    
    def get_trade_history(self) -> List[Dict]:
        """Get today's trade history."""
        return self._trade_history.copy()
