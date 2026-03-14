"""
Market Hours Scheduler (Module 17)
====================================
Trading window: 9:15 AM → 3:30 PM IST
Square off trades at 3:20 PM.
Handles pre-market, market hours, and post-market phases.
"""

import threading
import time as time_module
from datetime import datetime, time, timedelta
from typing import Callable, Dict, List, Optional, Any
from enum import Enum

from ai_trading_agent.utils.helpers import get_ist_now, is_market_hours, is_square_off_time, is_trading_day
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("MarketScheduler")


class MarketPhase(Enum):
    PRE_MARKET = "PRE_MARKET"
    MARKET_OPEN = "MARKET_OPEN"
    TRADING = "TRADING"
    SQUARE_OFF = "SQUARE_OFF"
    MARKET_CLOSED = "MARKET_CLOSED"
    WEEKEND = "WEEKEND"


class MarketScheduler:
    """
    Manages the trading schedule and executes callbacks at key times.
    
    Schedule:
    - 9:00 AM: Pre-market preparation
    - 9:15 AM: Market open / ORB setup
    - 9:30 AM: ORB period ends, trading begins
    - 3:20 PM: Square off all positions
    - 3:30 PM: Market close / daily summary
    
    Non-trading days: Weekends and holidays
    """
    
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Callbacks by phase
        self._callbacks: Dict[str, List[Callable]] = {
            "pre_market": [],
            "market_open": [],
            "orb_complete": [],
            "trading_tick": [],
            "square_off": [],
            "market_close": [],
            "daily_summary": [],
        }
        
        # Phase tracking
        self._current_phase = MarketPhase.MARKET_CLOSED
        self._phase_triggered: Dict[str, bool] = {}
        self._tick_interval = 5  # seconds between trading ticks
        
        logger.info("MarketScheduler initialized")
    
    def register_callback(self, phase: str, callback: Callable):
        """Register a callback for a specific market phase."""
        if phase in self._callbacks:
            self._callbacks[phase].append(callback)
            logger.debug(f"Registered callback for {phase}: {callback.__name__}")
        else:
            logger.warning(f"Unknown phase: {phase}")
    
    def start(self):
        """Start the scheduler."""
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("🕐 Market Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self._running = False
        logger.info("⏹️ Market Scheduler stopped")
    
    def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            now = get_ist_now()
            current_time = now.time()
            
            # Reset triggers at midnight
            if current_time < time(0, 1):
                self._phase_triggered = {}
            
            # Determine current phase
            new_phase = self._determine_phase(now)
            
            if new_phase != self._current_phase:
                logger.info(f"📅 Phase change: {self._current_phase.value} → {new_phase.value}")
                self._current_phase = new_phase
            
            # Execute phase callbacks
            self._execute_phase_callbacks(now)
            
            # Sleep based on phase
            if self._current_phase == MarketPhase.TRADING:
                time_module.sleep(self._tick_interval)
            elif self._current_phase in (MarketPhase.PRE_MARKET, MarketPhase.SQUARE_OFF):
                time_module.sleep(10)
            else:
                time_module.sleep(30)
    
    def _determine_phase(self, now: datetime) -> MarketPhase:
        """Determine current market phase."""
        if not is_trading_day(now):
            return MarketPhase.WEEKEND
        
        current_time = now.time()
        
        if current_time < time(9, 0):
            return MarketPhase.MARKET_CLOSED
        elif current_time < time(9, 15):
            return MarketPhase.PRE_MARKET
        elif current_time < time(9, 16):  # First minute
            return MarketPhase.MARKET_OPEN
        elif current_time < time(15, 20):
            return MarketPhase.TRADING
        elif current_time < time(15, 30):
            return MarketPhase.SQUARE_OFF
        else:
            return MarketPhase.MARKET_CLOSED
    
    def _execute_phase_callbacks(self, now: datetime):
        """Execute callbacks for the current phase."""
        current_time = now.time()
        
        # Pre-market (9:00 AM)
        if (self._current_phase == MarketPhase.PRE_MARKET and 
            not self._phase_triggered.get("pre_market")):
            self._trigger_callbacks("pre_market")
            self._phase_triggered["pre_market"] = True
        
        # Market open (9:15 AM)
        if (self._current_phase == MarketPhase.MARKET_OPEN and 
            not self._phase_triggered.get("market_open")):
            self._trigger_callbacks("market_open")
            self._phase_triggered["market_open"] = True
        
        # ORB complete (9:30 AM)
        if (current_time >= time(9, 30) and 
            not self._phase_triggered.get("orb_complete")):
            self._trigger_callbacks("orb_complete")
            self._phase_triggered["orb_complete"] = True
        
        # Trading ticks
        if self._current_phase == MarketPhase.TRADING:
            self._trigger_callbacks("trading_tick")
        
        # Square off (3:20 PM)
        if (self._current_phase == MarketPhase.SQUARE_OFF and 
            not self._phase_triggered.get("square_off")):
            self._trigger_callbacks("square_off")
            self._phase_triggered["square_off"] = True
        
        # Market close / daily summary (3:30 PM)
        if (current_time >= time(15, 30) and 
            not self._phase_triggered.get("market_close")):
            self._trigger_callbacks("market_close")
            self._trigger_callbacks("daily_summary")
            self._phase_triggered["market_close"] = True
    
    def _trigger_callbacks(self, phase: str):
        """Execute all callbacks for a given phase."""
        for callback in self._callbacks.get(phase, []):
            try:
                callback()
            except Exception as e:
                logger.error(f"Callback error in {phase}/{callback.__name__}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        now = get_ist_now()
        
        # Time to next phase
        next_phase, time_to_next = self._get_next_phase(now)
        
        return {
            "current_phase": self._current_phase.value,
            "current_time": now.strftime("%I:%M:%S %p IST"),
            "is_trading_day": is_trading_day(now),
            "is_market_hours": is_market_hours(now),
            "is_square_off_time": is_square_off_time(now),
            "next_phase": next_phase,
            "time_to_next": time_to_next,
            "scheduler_running": self._running,
            "tick_interval": self._tick_interval,
        }
    
    def _get_next_phase(self, now: datetime) -> tuple:
        """Calculate the next market phase and time until it."""
        current_time = now.time()
        
        phases = [
            (time(9, 0), "PRE_MARKET"),
            (time(9, 15), "MARKET_OPEN"),
            (time(9, 30), "TRADING_STARTS"),
            (time(15, 20), "SQUARE_OFF"),
            (time(15, 30), "MARKET_CLOSE"),
        ]
        
        for phase_time, phase_name in phases:
            if current_time < phase_time:
                dt_today = now.replace(
                    hour=phase_time.hour, minute=phase_time.minute, 
                    second=0, microsecond=0
                )
                diff = dt_today - now
                minutes = int(diff.total_seconds() / 60)
                return phase_name, f"{minutes} minutes"
        
        return "NEXT_DAY_PRE_MARKET", "Tomorrow 9:00 AM"
    
    def force_phase(self, phase: MarketPhase):
        """Force a specific phase (for testing)."""
        logger.warning(f"⚠️ Forcing phase to: {phase.value}")
        self._current_phase = phase
