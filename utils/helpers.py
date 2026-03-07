"""
Helper Utilities
================
Common utility functions used across the trading platform.
"""

import json
import hashlib
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional
import pytz


IST = pytz.timezone("Asia/Kolkata")


def get_ist_now() -> datetime:
    """Get current time in IST."""
    return datetime.now(IST)


def is_market_hours(now: Optional[datetime] = None) -> bool:
    """Check if current time is within market hours (9:15 AM - 3:30 PM IST)."""
    if now is None:
        now = get_ist_now()
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def is_square_off_time(now: Optional[datetime] = None) -> bool:
    """Check if it's time to square off positions (3:20 PM IST)."""
    if now is None:
        now = get_ist_now()
    square_off = now.replace(hour=15, minute=20, second=0, microsecond=0)
    return now >= square_off


def is_trading_day(now: Optional[datetime] = None) -> bool:
    """Check if today is a trading day (Monday-Friday, excluding holidays)."""
    if now is None:
        now = get_ist_now()
    return now.weekday() < 5  # Monday=0, Friday=4


def round_to_tick(price: float, tick_size: float = 0.05) -> float:
    """Round price to nearest tick size."""
    return round(round(price / tick_size) * tick_size, 2)


def calculate_lot_size(symbol: str) -> int:
    """Get lot size for given symbol."""
    lot_sizes = {
        "NIFTY": 25,
        "BANKNIFTY": 15,
        "SENSEX": 10,
    }
    return lot_sizes.get(symbol.upper(), 25)


def get_expiry_date(symbol: str, weekly: bool = True) -> str:
    """Calculate nearest expiry date for the given symbol."""
    now = get_ist_now()
    
    if symbol.upper() in ["NIFTY", "BANKNIFTY"]:
        # Weekly expiry on Thursday
        days_until_thursday = (3 - now.weekday()) % 7
        if days_until_thursday == 0 and now.hour >= 15:
            days_until_thursday = 7
        expiry = now + timedelta(days=days_until_thursday)
    else:
        # Monthly expiry - last Thursday of month
        import calendar
        year, month = now.year, now.month
        last_day = calendar.monthrange(year, month)[1]
        last_date = datetime(year, month, last_day, tzinfo=IST)
        while last_date.weekday() != 3:  # Thursday
            last_date -= timedelta(days=1)
        expiry = last_date
    
    return expiry.strftime("%d%b%Y").upper()


def format_currency(amount: float) -> str:
    """Format amount in Indian Rupees."""
    if abs(amount) >= 10_000_000:
        return f"₹{amount / 10_000_000:.2f} Cr"
    elif abs(amount) >= 100_000:
        return f"₹{amount / 100_000:.2f} L"
    else:
        return f"₹{amount:,.2f}"


def generate_signal_id(symbol: str, strike: int, option_type: str) -> str:
    """Generate unique signal ID."""
    timestamp = get_ist_now().strftime("%Y%m%d%H%M%S")
    raw = f"{symbol}_{strike}_{option_type}_{timestamp}"
    return hashlib.md5(raw.encode()).hexdigest()[:12].upper()


def calculate_risk_reward(entry: float, target: float, stop_loss: float) -> float:
    """Calculate risk-reward ratio."""
    risk = abs(entry - stop_loss)
    reward = abs(target - entry)
    if risk == 0:
        return 0.0
    return round(reward / risk, 2)


def get_strike_interval(symbol: str) -> int:
    """Get strike price interval for a given symbol."""
    intervals = {
        "NIFTY": 50,
        "BANKNIFTY": 100,
        "SENSEX": 100,
    }
    return intervals.get(symbol.upper(), 50)


def get_atm_strike(spot_price: float, symbol: str) -> int:
    """Calculate ATM (At The Money) strike price."""
    interval = get_strike_interval(symbol)
    return int(round(spot_price / interval) * interval)


def format_signal_message(signal: Dict[str, Any]) -> str:
    """Format a trading signal into a readable message."""
    msg = f"""
🔔 <b>TRADE SIGNAL</b>

📊 <b>{signal.get('symbol', 'N/A')} {signal.get('strike', 'N/A')} {signal.get('option_type', 'N/A')}</b>

🟢 BUY ABOVE: {signal.get('entry_price', 'N/A')}
🎯 TARGET: {signal.get('target1', 'N/A')} / {signal.get('target2', 'N/A')}
🔴 STOP LOSS: {signal.get('stop_loss', 'N/A')}

📈 TRADE SCORE: {signal.get('trade_score', 'N/A')}%
🤖 AGENTS CONFIRMING: {signal.get('confirming_agents', 'N/A')}/{signal.get('total_agents', 'N/A')}
📊 REGIME: {signal.get('market_regime', 'N/A')}

⏰ {get_ist_now().strftime("%d-%b-%Y %I:%M %p")} IST
"""
    return msg.strip()
