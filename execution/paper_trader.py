"""
Paper Trading Execution Engine (Module 14)
============================================
Simulates order execution for paper trading mode.
Tracks: balance, positions, profit/loss, trade history, win rate.
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import numpy as np

from ai_trading_agent.config import TradingConfig
from ai_trading_agent.risk.risk_manager import RiskManager
from ai_trading_agent.utils.helpers import format_currency, get_ist_now, generate_signal_id
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("PaperTrader")


class OrderStatus(Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PARTIAL = "PARTIAL"


@dataclass
class PaperOrder:
    """Simulated order."""
    order_id: str
    symbol: str
    strike: int
    option_type: str  # CE or PE
    direction: str  # BUY or SELL
    quantity: int
    price: float
    order_type: str = "MARKET"  # MARKET, LIMIT
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PaperPosition:
    """Simulated open position."""
    position_id: str
    symbol: str
    strike: int
    option_type: str
    quantity: int
    entry_price: float
    current_price: float = 0.0
    target1: float = 0.0
    target2: float = 0.0
    stop_loss: float = 0.0
    unrealized_pnl: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    entry_time: datetime = field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    exit_price: float = 0.0
    realized_pnl: float = 0.0
    exit_reason: str = ""


class PaperTradingEngine:
    """
    Simulates live trading in paper mode.
    
    Features:
    - Order simulation with realistic fills
    - Position tracking with SL/Target monitoring
    - Balance and P&L management
    - Trade history and statistics
    - Auto square-off at 3:20 PM
    """
    
    def __init__(self, config: TradingConfig, risk_manager: RiskManager):
        self.config = config
        self.risk_manager = risk_manager
        
        self._balance = config.initial_capital
        self._positions: Dict[str, PaperPosition] = {}
        self._orders: List[PaperOrder] = []
        self._closed_trades: List[Dict] = []
        self._daily_pnl = 0.0
        
        # Statistics
        self._stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "max_profit": 0.0,
            "max_loss": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
        }
        
        # Data directory
        self._data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(self._data_dir, exist_ok=True)
        
        logger.info(f"PaperTradingEngine initialized | Balance: {format_currency(self._balance)}")
    
    def execute_signal(self, signal: Dict[str, Any]) -> Optional[PaperPosition]:
        """
        Execute a trade signal in paper trading mode.
        
        Args:
            signal: Trade signal with entry, targets, stop loss
            
        Returns:
            PaperPosition if executed, None if rejected
        """
        # Pre-trade risk check
        risk_check = self.risk_manager.check_trade_allowed()
        if not risk_check['allowed']:
            logger.warning(f"🚫 Trade rejected: {risk_check['reasons']}")
            return None
        
        symbol = signal.get('symbol', 'UNKNOWN')
        strike = signal.get('strike', 0)
        option_type = signal.get('option_type', 'CE')
        entry_price = signal.get('entry_price', 0)
        target1 = signal.get('target1', 0)
        target2 = signal.get('target2', 0)
        stop_loss = signal.get('stop_loss', 0)
        
        if entry_price <= 0:
            logger.warning("Invalid entry price")
            return None
        
        # Calculate position size
        sizing = self.risk_manager.calculate_position_size(entry_price, stop_loss)
        quantity = sizing.get('quantity', 1)
        
        # Simulate order execution
        # Add small slippage (0.1% average)
        slippage = entry_price * np.random.uniform(0, 0.002)
        filled_price = round(entry_price + slippage, 2)
        
        # Create order
        order_id = generate_signal_id(symbol, strike, option_type)
        order = PaperOrder(
            order_id=order_id,
            symbol=symbol,
            strike=strike,
            option_type=option_type,
            direction="BUY",
            quantity=quantity,
            price=entry_price,
            filled_price=filled_price,
            status=OrderStatus.EXECUTED
        )
        self._orders.append(order)
        
        # Create position
        position_id = f"POS_{order_id}"
        position = PaperPosition(
            position_id=position_id,
            symbol=symbol,
            strike=strike,
            option_type=option_type,
            quantity=quantity,
            entry_price=filled_price,
            current_price=filled_price,
            target1=target1,
            target2=target2,
            stop_loss=stop_loss,
        )
        
        self._positions[position_id] = position
        
        # Deduct from balance
        trade_cost = filled_price * quantity
        self._balance -= trade_cost
        
        logger.info(
            f"✅ Paper Trade Executed | {symbol} {strike} {option_type} | "
            f"Qty: {quantity} @ {filled_price} | Cost: {format_currency(trade_cost)}"
        )
        
        return position
    
    def update_positions(self, market_prices: Dict[str, float]):
        """
        Update all open positions with current market prices.
        
        Args:
            market_prices: Dict of position_id -> current_price or symbol_strike_type -> price
        """
        for pos_id, position in list(self._positions.items()):
            if position.status != PositionStatus.OPEN:
                continue
            
            # Get current price
            key = f"{position.symbol}_{position.strike}_{position.option_type}"
            current_price = market_prices.get(key)
            
            if current_price is None:
                # Simulate price movement
                change = np.random.normal(0, position.entry_price * 0.02)
                current_price = max(1, position.current_price + change)
            
            position.current_price = round(current_price, 2)
            position.unrealized_pnl = round(
                (current_price - position.entry_price) * position.quantity, 2
            )
            
            # Check stop loss
            if current_price <= position.stop_loss:
                self._close_position(pos_id, current_price, "SL_HIT")
            
            # Check target 1
            elif current_price >= position.target1:
                # Book partial (or full if no target2)
                if position.target2 > 0 and current_price < position.target2:
                    # Hold for target 2 (in real system, would book partial)
                    pass
                else:
                    self._close_position(pos_id, current_price, "TARGET_HIT")
            
            # Check target 2
            elif position.target2 > 0 and current_price >= position.target2:
                self._close_position(pos_id, current_price, "TARGET2_HIT")
    
    def _close_position(self, position_id: str, exit_price: float, reason: str):
        """Close a position and record the trade."""
        if position_id not in self._positions:
            return
        
        position = self._positions[position_id]
        position.status = PositionStatus.CLOSED
        position.exit_price = round(exit_price, 2)
        position.exit_time = datetime.now()
        position.exit_reason = reason
        
        # Calculate P&L
        pnl = round((exit_price - position.entry_price) * position.quantity, 2)
        position.realized_pnl = pnl
        
        # Update balance
        self._balance += (exit_price * position.quantity)
        self._daily_pnl += pnl
        
        # Update stats
        self._stats['total_trades'] += 1
        self._stats['total_pnl'] += pnl
        
        if pnl > 0:
            self._stats['winning_trades'] += 1
            self._stats['largest_win'] = max(self._stats['largest_win'], pnl)
        elif pnl < 0:
            self._stats['losing_trades'] += 1
            self._stats['largest_loss'] = min(self._stats['largest_loss'], pnl)
        
        # Record in risk manager
        self.risk_manager.record_trade({
            'symbol': position.symbol,
            'strike': position.strike,
            'option_type': position.option_type,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'quantity': position.quantity,
            'pnl': pnl,
            'reason': reason
        })
        
        # Move to closed trades
        self._closed_trades.append({
            'position_id': position_id,
            'symbol': position.symbol,
            'strike': position.strike,
            'option_type': position.option_type,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'quantity': position.quantity,
            'pnl': pnl,
            'reason': reason,
            'entry_time': position.entry_time.isoformat(),
            'exit_time': position.exit_time.isoformat() if position.exit_time else "",
            'duration_seconds': (position.exit_time - position.entry_time).total_seconds() 
                if position.exit_time else 0
        })
        
        pnl_emoji = "💚" if pnl > 0 else "❤️"
        logger.info(
            f"{pnl_emoji} Position Closed | {position.symbol} {position.strike} {position.option_type} | "
            f"Entry: {position.entry_price} → Exit: {exit_price} | "
            f"P&L: {format_currency(pnl)} | Reason: {reason}"
        )
        
        # Remove from active positions
        del self._positions[position_id]
    
    def square_off_all(self, reason: str = "SQUARE_OFF"):
        """Close all open positions (e.g., at 3:20 PM)."""
        open_positions = [
            (pid, pos) for pid, pos in self._positions.items() 
            if pos.status == PositionStatus.OPEN
        ]
        
        for pos_id, pos in open_positions:
            self._close_position(pos_id, pos.current_price, reason)
        
        logger.info(f"📤 Squared off {len(open_positions)} positions | Reason: {reason}")
    
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions."""
        return [
            {
                'position_id': pos.position_id,
                'symbol': pos.symbol,
                'strike': pos.strike,
                'option_type': pos.option_type,
                'quantity': pos.quantity,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'unrealized_pnl': pos.unrealized_pnl,
                'target1': pos.target1,
                'target2': pos.target2,
                'stop_loss': pos.stop_loss,
                'entry_time': pos.entry_time.isoformat()
            }
            for pos in self._positions.values()
            if pos.status == PositionStatus.OPEN
        ]
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get complete portfolio status."""
        open_positions = self.get_open_positions()
        total_unrealized = sum(p['unrealized_pnl'] for p in open_positions)
        
        win_rate = (self._stats['winning_trades'] / self._stats['total_trades'] * 100) \
            if self._stats['total_trades'] > 0 else 0
        
        return {
            "balance": round(self._balance, 2),
            "daily_pnl": round(self._daily_pnl, 2),
            "unrealized_pnl": round(total_unrealized, 2),
            "total_pnl": round(self._daily_pnl + total_unrealized, 2),
            "open_positions": len(open_positions),
            "positions": open_positions,
            "total_trades": self._stats['total_trades'],
            "winning_trades": self._stats['winning_trades'],
            "losing_trades": self._stats['losing_trades'],
            "win_rate": round(win_rate, 2),
            "largest_win": round(self._stats['largest_win'], 2),
            "largest_loss": round(self._stats['largest_loss'], 2),
        }
    
    def save_state(self):
        """Save current state to disk."""
        state = {
            "balance": self._balance,
            "daily_pnl": self._daily_pnl,
            "stats": self._stats,
            "closed_trades": self._closed_trades,
            "timestamp": datetime.now().isoformat()
        }
        
        path = os.path.join(self._data_dir, "paper_trading_state.json")
        with open(path, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        
        logger.info(f"💾 Paper trading state saved")
    
    def load_state(self) -> bool:
        """Load state from disk."""
        path = os.path.join(self._data_dir, "paper_trading_state.json")
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    state = json.load(f)
                self._balance = state.get('balance', self.config.initial_capital)
                self._stats = state.get('stats', self._stats)
                logger.info(f"📂 Paper trading state loaded | Balance: {format_currency(self._balance)}")
                return True
        except Exception as e:
            logger.error(f"Error loading state: {e}")
        return False
