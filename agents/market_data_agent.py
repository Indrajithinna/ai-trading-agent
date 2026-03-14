"""
Market Data Agent (Module 1)
============================
Collects real-time market data from Flattrade API.
Supports REST polling and WebSocket streaming.
Fetches: price, volume, OHLC, option chain data.
"""

import time
import json
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

import requests
import pandas as pd
import numpy as np

from ai_trading_agent.config import FlattradeConfig, MarketConfig
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("MarketDataAgent")


@dataclass
class MarketTick:
    """Represents a single market tick."""
    symbol: str
    ltp: float  # Last Traded Price
    open: float
    high: float
    low: float
    close: float
    volume: int
    oi: int = 0  # Open Interest
    timestamp: datetime = field(default_factory=datetime.now)
    bid: float = 0.0
    ask: float = 0.0
    bid_qty: int = 0
    ask_qty: int = 0


@dataclass
class OHLCBar:
    """Represents an OHLC candlestick bar."""
    symbol: str
    timeframe: int  # minutes
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime = field(default_factory=datetime.now)


class MarketDataAgent:
    """
    Agent responsible for collecting and managing all market data.
    
    Features:
    - REST API polling for snapshots
    - WebSocket streaming for real-time ticks
    - OHLC bar construction for multiple timeframes
    - Option chain data fetching
    - Data caching and history management
    """
    
    def __init__(self, flattrade_config: FlattradeConfig, market_config: MarketConfig):
        self.ft_config = flattrade_config
        self.mkt_config = market_config
        
        self._token: Optional[str] = None
        self._ws = None
        self._ws_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Data stores
        self._ticks: Dict[str, List[MarketTick]] = {}
        self._ohlc: Dict[str, Dict[int, List[OHLCBar]]] = {}
        self._option_chains: Dict[str, pd.DataFrame] = {}
        self._spot_prices: Dict[str, float] = {}
        
        # Callbacks
        self._tick_callbacks: List[Callable] = []
        self._bar_callbacks: Dict[int, List[Callable]] = {}
        
        # Bar construction state
        self._current_bars: Dict[str, Dict[int, OHLCBar]] = {}
        self._last_bar_time: Dict[str, Dict[int, datetime]] = {}
        
        # Simulated data mode
        self._simulation_mode = True
        
        logger.info("MarketDataAgent initialized")
    
    def authenticate(self) -> bool:
        """Authenticate with Flattrade API."""
        try:
            if not self.ft_config.api_key or not self.ft_config.api_secret:
                logger.warning("Flattrade credentials not set. Running in simulation mode.")
                self._simulation_mode = True
                return True
            
            # Generate request token
            api_hash = hashlib.sha256(
                f"{self.ft_config.api_key}{self.ft_config.api_secret}".encode()
            ).hexdigest()
            
            payload = {
                "api_key": self.ft_config.api_key,
                "request_code": api_hash,
            }
            
            response = requests.post(
                f"{self.ft_config.base_url}{self.ft_config.login_endpoint}",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self._token = data.get("token")
                self._simulation_mode = False
                logger.info("✅ Flattrade authentication successful")
                return True
            else:
                logger.error(f"❌ Authentication failed: {response.text}")
                self._simulation_mode = True
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            self._simulation_mode = True
            return True  # Fall back to simulation
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}" if self._token else ""
        }
    
    def get_spot_price(self, symbol: str) -> float:
        """Get current spot price for a symbol."""
        if self._simulation_mode:
            return self._get_simulated_price(symbol)
        
        try:
            payload = {
                "uid": self.ft_config.client_id,
                "exch": "NSE",
                "token": self._get_symbol_token(symbol)
            }
            response = requests.post(
                f"{self.ft_config.base_url}{self.ft_config.scripinfo_endpoint}",
                headers=self._get_headers(),
                json=payload,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                price = float(data.get("lp", 0))
                self._spot_prices[symbol] = price
                return price
        except Exception as e:
            logger.error(f"Error fetching spot price for {symbol}: {e}")
        
        return self._spot_prices.get(symbol, self._get_simulated_price(symbol))
    
    def get_ohlc_data(self, symbol: str, timeframe: int, bars: int = 100) -> pd.DataFrame:
        """
        Get OHLC data for a symbol and timeframe.
        
        Args:
            symbol: Trading symbol (NIFTY, BANKNIFTY, SENSEX)
            timeframe: Candle timeframe in minutes (1, 5, 15)
            bars: Number of bars to return
        """
        if self._simulation_mode:
            return self._generate_simulated_ohlc(symbol, timeframe, bars)
        
        key = f"{symbol}_{timeframe}"
        if key in self._ohlc and symbol in self._ohlc:
            if timeframe in self._ohlc[symbol]:
                bar_list = self._ohlc[symbol][timeframe][-bars:]
                return self._bars_to_dataframe(bar_list)
        
        return self._generate_simulated_ohlc(symbol, timeframe, bars)
    
    def get_option_chain(self, symbol: str, expiry: str = "") -> pd.DataFrame:
        """Fetch option chain data for a symbol."""
        if self._simulation_mode:
            return self._generate_simulated_option_chain(symbol)
        
        try:
            payload = {
                "uid": self.ft_config.client_id,
                "exch": "NFO",
                "tsym": symbol,
                "strprc": str(int(self.get_spot_price(symbol))),
                "cnt": "10"
            }
            
            response = requests.post(
                f"{self.ft_config.base_url}{self.ft_config.optionchain_endpoint}",
                headers=self._get_headers(),
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data.get("values", []))
                self._option_chains[symbol] = df
                return df
                
        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}")
        
        return self._generate_simulated_option_chain(symbol)
    
    def subscribe_ticks(self, symbols: List[str], callback: Callable):
        """Subscribe to real-time tick updates."""
        self._tick_callbacks.append(callback)
        
        if self._simulation_mode:
            logger.info(f"📡 Subscribed to simulated ticks for: {symbols}")
            return
        
        # WebSocket subscription would go here for live API
        logger.info(f"📡 Subscribed to live ticks for: {symbols}")
    
    def subscribe_bars(self, timeframe: int, callback: Callable):
        """Subscribe to OHLC bar completions."""
        if timeframe not in self._bar_callbacks:
            self._bar_callbacks[timeframe] = []
        self._bar_callbacks[timeframe].append(callback)
    
    def start_streaming(self):
        """Start the data streaming engine."""
        self._running = True
        
        if self._simulation_mode:
            self._ws_thread = threading.Thread(
                target=self._simulate_stream, daemon=True
            )
            self._ws_thread.start()
            logger.info("🔄 Simulated data streaming started")
        else:
            self._ws_thread = threading.Thread(
                target=self._connect_websocket, daemon=True
            )
            self._ws_thread.start()
            logger.info("🔄 Live data streaming started")
    
    def stop_streaming(self):
        """Stop the data streaming engine."""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except:
                pass
        logger.info("⏹️ Data streaming stopped")
    
    def _connect_websocket(self):
        """Connect to Flattrade WebSocket for live streaming."""
        try:
            import websocket
            
            def on_message(ws, message):
                data = json.loads(message)
                self._process_tick(data)
            
            def on_error(ws, error):
                logger.error(f"WebSocket error: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                logger.warning("WebSocket connection closed")
            
            def on_open(ws):
                logger.info("WebSocket connection opened")
                # Subscribe to symbols
                for symbol in self.mkt_config.markets:
                    sub_msg = {
                        "t": "t",
                        "k": f"NSE|{self._get_symbol_token(symbol)}"
                    }
                    ws.send(json.dumps(sub_msg))
            
            self._ws = websocket.WebSocketApp(
                self.ft_config.ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open,
                header={"Authorization": self._token}
            )
            self._ws.run_forever()
            
        except ImportError:
            logger.warning("websocket-client not installed. Falling back to simulation.")
            self._simulation_mode = True
            self._simulate_stream()
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
    
    def _process_tick(self, data: Dict):
        """Process incoming tick data."""
        try:
            symbol = data.get("ts", data.get("symbol", "UNKNOWN"))
            tick = MarketTick(
                symbol=symbol,
                ltp=float(data.get("lp", 0)),
                open=float(data.get("o", 0)),
                high=float(data.get("h", 0)),
                low=float(data.get("lo", 0)),
                close=float(data.get("c", 0)),
                volume=int(data.get("v", 0)),
                oi=int(data.get("oi", 0)),
                bid=float(data.get("bp1", 0)),
                ask=float(data.get("sp1", 0)),
                bid_qty=int(data.get("bq1", 0)),
                ask_qty=int(data.get("sq1", 0)),
                timestamp=datetime.now()
            )
            
            if symbol not in self._ticks:
                self._ticks[symbol] = []
            self._ticks[symbol].append(tick)
            
            # Keep last 5000 ticks
            if len(self._ticks[symbol]) > 5000:
                self._ticks[symbol] = self._ticks[symbol][-5000:]
            
            # Update spot price
            self._spot_prices[symbol] = tick.ltp
            
            # Update OHLC bars
            self._update_bars(tick)
            
            # Notify callbacks
            for callback in self._tick_callbacks:
                try:
                    callback(tick)
                except Exception as e:
                    logger.error(f"Tick callback error: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing tick: {e}")
    
    def _update_bars(self, tick: MarketTick):
        """Update OHLC bars with new tick data."""
        for timeframe in [1, 5, 15]:
            key = f"{tick.symbol}_{timeframe}"
            
            if tick.symbol not in self._current_bars:
                self._current_bars[tick.symbol] = {}
                self._last_bar_time[tick.symbol] = {}
            
            now = tick.timestamp
            bar_start = now.replace(
                minute=(now.minute // timeframe) * timeframe,
                second=0, microsecond=0
            )
            
            if timeframe not in self._current_bars[tick.symbol]:
                self._current_bars[tick.symbol][timeframe] = OHLCBar(
                    symbol=tick.symbol,
                    timeframe=timeframe,
                    open=tick.ltp,
                    high=tick.ltp,
                    low=tick.ltp,
                    close=tick.ltp,
                    volume=tick.volume,
                    timestamp=bar_start
                )
                self._last_bar_time[tick.symbol][timeframe] = bar_start
            else:
                current_bar = self._current_bars[tick.symbol][timeframe]
                
                if bar_start > self._last_bar_time[tick.symbol][timeframe]:
                    # New bar - save the completed bar
                    if tick.symbol not in self._ohlc:
                        self._ohlc[tick.symbol] = {}
                    if timeframe not in self._ohlc[tick.symbol]:
                        self._ohlc[tick.symbol][timeframe] = []
                    
                    self._ohlc[tick.symbol][timeframe].append(current_bar)
                    
                    # Keep last 500 bars
                    if len(self._ohlc[tick.symbol][timeframe]) > 500:
                        self._ohlc[tick.symbol][timeframe] = \
                            self._ohlc[tick.symbol][timeframe][-500:]
                    
                    # Notify bar callbacks
                    for callback in self._bar_callbacks.get(timeframe, []):
                        try:
                            callback(current_bar)
                        except Exception as e:
                            logger.error(f"Bar callback error: {e}")
                    
                    # Start new bar
                    self._current_bars[tick.symbol][timeframe] = OHLCBar(
                        symbol=tick.symbol,
                        timeframe=timeframe,
                        open=tick.ltp,
                        high=tick.ltp,
                        low=tick.ltp,
                        close=tick.ltp,
                        volume=tick.volume,
                        timestamp=bar_start
                    )
                    self._last_bar_time[tick.symbol][timeframe] = bar_start
                else:
                    # Update current bar
                    current_bar.high = max(current_bar.high, tick.ltp)
                    current_bar.low = min(current_bar.low, tick.ltp)
                    current_bar.close = tick.ltp
                    current_bar.volume += tick.volume
    
    def _simulate_stream(self):
        """Simulate market data stream for paper trading."""
        logger.info("🎭 Starting simulated data stream")
        
        base_prices = {
            "NIFTY": 24250.0,
            "BANKNIFTY": 51500.0,
            "SENSEX": 79800.0
        }
        
        while self._running:
            for symbol in self.mkt_config.markets:
                base = base_prices.get(symbol, 24000.0)
                # Random walk with mean reversion
                change = np.random.normal(0, base * 0.0003)
                base_prices[symbol] = base + change
                price = base_prices[symbol]
                
                tick_data = {
                    "ts": symbol,
                    "lp": round(price, 2),
                    "o": round(price - np.random.uniform(0, 20), 2),
                    "h": round(price + np.random.uniform(0, 30), 2),
                    "lo": round(price - np.random.uniform(0, 30), 2),
                    "c": round(price, 2),
                    "v": int(np.random.uniform(100000, 500000)),
                    "oi": int(np.random.uniform(500000, 2000000)),
                    "bp1": round(price - 0.5, 2),
                    "sp1": round(price + 0.5, 2),
                    "bq1": int(np.random.uniform(100, 1000)),
                    "sq1": int(np.random.uniform(100, 1000)),
                }
                self._process_tick(tick_data)
            
            time.sleep(1)  # 1 second between ticks
    
    def _get_simulated_price(self, symbol: str) -> float:
        """Get simulated spot price."""
        if symbol in self._spot_prices:
            return self._spot_prices[symbol]
        
        prices = {
            "NIFTY": 24250.0 + np.random.uniform(-50, 50),
            "BANKNIFTY": 51500.0 + np.random.uniform(-100, 100),
            "SENSEX": 79800.0 + np.random.uniform(-150, 150),
        }
        return prices.get(symbol.upper(), 24000.0)
    
    def _generate_simulated_ohlc(self, symbol: str, timeframe: int, bars: int) -> pd.DataFrame:
        """Generate simulated OHLC data for backtesting/paper trading."""
        base_price = self._get_simulated_price(symbol)
        
        dates = pd.date_range(
            end=datetime.now(),
            periods=bars,
            freq=f"{timeframe}min"
        )
        
        data = []
        price = base_price
        
        for dt in dates:
            change = np.random.normal(0, price * 0.001)
            open_price = price
            close_price = price + change
            high_price = max(open_price, close_price) + abs(np.random.normal(0, price * 0.0005))
            low_price = min(open_price, close_price) - abs(np.random.normal(0, price * 0.0005))
            volume = int(np.random.uniform(50000, 200000))
            
            data.append({
                "timestamp": dt,
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": volume
            })
            price = close_price
        
        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df
    
    def _generate_simulated_option_chain(self, symbol: str) -> pd.DataFrame:
        """Generate simulated option chain data."""
        spot = self._get_simulated_price(symbol)
        interval = {"NIFTY": 50, "BANKNIFTY": 100, "SENSEX": 100}.get(symbol, 50)
        atm = int(round(spot / interval) * interval)
        
        strikes = list(range(atm - interval * 10, atm + interval * 11, interval))
        
        data = []
        for strike in strikes:
            moneyness = (spot - strike) / spot
            
            # Simple Black-Scholes approximation for simulation
            ce_price = max(5, spot - strike + np.random.uniform(10, 50)) if strike < spot \
                else max(2, np.random.uniform(5, 80) * np.exp(-abs(moneyness) * 10))
            pe_price = max(5, strike - spot + np.random.uniform(10, 50)) if strike > spot \
                else max(2, np.random.uniform(5, 80) * np.exp(-abs(moneyness) * 10))
            
            data.append({
                "strike": strike,
                "ce_ltp": round(ce_price, 2),
                "ce_oi": int(np.random.uniform(100000, 5000000)),
                "ce_volume": int(np.random.uniform(10000, 500000)),
                "ce_iv": round(np.random.uniform(10, 35), 2),
                "ce_bid": round(ce_price - 0.5, 2),
                "ce_ask": round(ce_price + 0.5, 2),
                "pe_ltp": round(pe_price, 2),
                "pe_oi": int(np.random.uniform(100000, 5000000)),
                "pe_volume": int(np.random.uniform(10000, 500000)),
                "pe_iv": round(np.random.uniform(10, 35), 2),
                "pe_bid": round(pe_price - 0.5, 2),
                "pe_ask": round(pe_price + 0.5, 2),
            })
        
        return pd.DataFrame(data)
    
    def _get_symbol_token(self, symbol: str) -> str:
        """Map symbol name to exchange token."""
        tokens = {
            "NIFTY": "26000",
            "BANKNIFTY": "26009",
            "SENSEX": "1",
        }
        return tokens.get(symbol.upper(), "26000")
    
    def _bars_to_dataframe(self, bars: List[OHLCBar]) -> pd.DataFrame:
        """Convert list of OHLCBar objects to pandas DataFrame."""
        data = [{
            "timestamp": b.timestamp,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume
        } for b in bars]
        
        df = pd.DataFrame(data)
        if not df.empty:
            df.set_index("timestamp", inplace=True)
        return df
    
    def get_latest_data(self, symbol: str) -> Dict[str, Any]:
        """Get a summary of latest data for a symbol."""
        return {
            "symbol": symbol,
            "spot_price": self._spot_prices.get(symbol, 0),
            "tick_count": len(self._ticks.get(symbol, [])),
            "last_tick": self._ticks[symbol][-1].__dict__ if symbol in self._ticks and self._ticks[symbol] else None,
            "simulation_mode": self._simulation_mode
        }
