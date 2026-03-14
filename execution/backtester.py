"""
Backtesting Engine
===================
Runs strategies against 5–10 years of real NIFTY / BANKNIFTY / SENSEX
historical data (fetched via yfinance) and produces detailed analytics.

Usage:
    python -m ai_trading_agent.main --mode backtest
    python -m ai_trading_agent.main --mode backtest --years 10 --symbol NIFTY
"""

import os
import sys
import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from copy import deepcopy

import numpy as np
import pandas as pd

# ── project imports ──────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ai_trading_agent.config import StrategyConfig, TradingConfig, load_config
from ai_trading_agent.agents.feature_engineering_agent import FeatureEngineeringAgent
from ai_trading_agent.strategies.vwap_strategy import VWAPBreakoutStrategy
from ai_trading_agent.strategies.ema_strategy import EMAMomentumStrategy
from ai_trading_agent.strategies.orb_strategy import ORBStrategy
from ai_trading_agent.strategies.base_strategy import SignalType
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("Backtester")


# ═══════════════════════════════════════════════════════════════════════════════
#  Yahoo-Finance Data Loader
# ═══════════════════════════════════════════════════════════════════════════════

# Mapping from our internal symbol names to Yahoo Finance tickers
YAHOO_TICKER_MAP = {
    "NIFTY":     "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX":    "^BSESN",
}


def fetch_historical_data(
    symbol: str,
    years: float = 1.0,
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Fetch *real* historical OHLCV data from Yahoo Finance.

    Args:
        symbol:   Internal symbol name (NIFTY / BANKNIFTY / SENSEX).
        years:    Number of years of history to fetch (5–10).
        interval: Bar interval – "1d" (daily), "1wk", "1h", etc.

    Returns:
        DataFrame with columns [open, high, low, close, volume].
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance is not installed. Run:  pip install yfinance")
        raise

    ticker = YAHOO_TICKER_MAP.get(symbol.upper(), f"^NSEI")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)

    logger.info(
        f"📥 Downloading {symbol} ({ticker}) data "
        f"from {start_date:%Y-%m-%d} to {end_date:%Y-%m-%d} …"
    )

    df = yf.download(
        ticker,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        interval=interval,
        progress=False,
        auto_adjust=True,
    )

    if df.empty:
        raise ValueError(f"No data returned for {ticker}")

    # Flatten multi-index columns or normalize standard columns
    df.columns = [c[0].lower() if isinstance(c, tuple) else str(c).lower() for c in df.columns]
    
    # Ensure required columns exist
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing column '{col}' in downloaded data")

    df = df[required_cols].copy()
    df.dropna(inplace=True)
    df.index.name = "timestamp"

    logger.info(f"✅ Loaded {len(df)} bars for {symbol}")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
#  Internal Trade Accounting
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BacktestTrade:
    """One round-trip backtest trade."""
    trade_id: int
    symbol: str
    strategy: str
    direction: str          # "BUY_CALL" or "BUY_PUT"
    entry_price: float
    target1: float
    target2: float
    stop_loss: float
    confidence: float
    entry_date: str
    exit_price: float = 0.0
    exit_date: str = ""
    exit_reason: str = ""   # "TARGET1", "TARGET2", "STOPLOSS", "EOD"
    pnl: float = 0.0
    pnl_pct: float = 0.0
    bars_held: int = 0
    is_winner: bool = False
    quantity: int = 0             # Qty determined at entry
    allocated_at_entry: float = 0.0  # Captures sizing at entry for PnL calculation


# ═══════════════════════════════════════════════════════════════════════════════
#  Backtest Engine
# ═══════════════════════════════════════════════════════════════════════════════

class BacktestEngine:
    """
    Fast-forward backtesting engine.

    1. Loads N years of real OHLCV data via Yahoo Finance.
    2. Walks forward bar-by-bar computing features and running strategies.
    3. Emulates paper-trade accounting (entry, TP, SL, EOD exit).
    4. Outputs a rich analytics report at the end.
    """

    LOOKBACK = 100          # minimum bars before first signal evaluation
    MAX_DAILY_TRADES = 1    # per-day trade cap
    MAX_OPEN_POSITIONS = 1  # concurrent positions
    ALLOCATION = 0.95       # Percent of balance per trade (95%)

    def __init__(
        self,
        symbols: List[str] | None = None,
        years: float = 1.0,
        initial_capital: float = 100_000.0,
        position_size_pct: float = 0.02,
    ):
        self.config = load_config()
        self.symbols = symbols or self.config.market.markets
        self.years = max(0.1, min(years, 10))
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct

        # modules
        self.feature_engine = FeatureEngineeringAgent()
        strategy_config = self.config.strategy
        self.strategies = {
            "VWAP":  VWAPBreakoutStrategy(strategy_config),
            "EMA":   EMAMomentumStrategy(strategy_config),
            "ORB":   ORBStrategy(strategy_config),
        }

        # runtime state
        self._capital = initial_capital
        self._trades: List[BacktestTrade] = []
        self._open_positions: List[BacktestTrade] = []
        self._trade_counter = 0
        self._daily_trade_counts: Dict[str, int] = defaultdict(int)
        self._equity_curve: List[Tuple[str, float]] = []

        # per-bar stats
        self._total_bars_processed = 0

    # ──────────────────────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        """Execute the full back-test and return summary dict."""
        logger.info("=" * 70)
        logger.info("🔬 BACKTESTING ENGINE — STARTING")
        logger.info(f"📅 Period : last {self.years} years")
        logger.info(f"📈 Symbols: {', '.join(self.symbols)}")
        logger.info(f"💰 Capital: ₹{self.initial_capital:,.0f}")
        logger.info("=" * 70)

        all_results: Dict[str, Dict] = {}

        for symbol in self.symbols:
            try:
                result = self._backtest_symbol(symbol)
                all_results[symbol] = result
            except Exception as e:
                logger.error(f"❌ Backtest failed for {symbol}: {e}", exc_info=True)

        # ── aggregate report ─────────────────────────────────────────────
        report = self._compile_report(all_results)

        # save JSON
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data"
        )
        os.makedirs(data_dir, exist_ok=True)
        json_path = os.path.join(data_dir, "backtest_report.json")
        with open(json_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"📄 JSON report saved → {json_path}")

        # generate HTML analytics
        try:
            from ai_trading_agent.execution.backtest_analytics import (
                generate_html_report,
            )
            html_path = os.path.join(data_dir, "backtest_report.html")
            generate_html_report(report, html_path)
            logger.info(f"📊 HTML analytics saved → {html_path}")
        except Exception as e:
            logger.warning(f"Could not generate HTML report: {e}")

        self._print_summary(report)
        return report

    # ──────────────────────────────────────────────────────────────────────────
    #  Per-symbol backtest loop
    # ──────────────────────────────────────────────────────────────────────────

    def _backtest_symbol(self, symbol: str) -> Dict[str, Any]:
        """Run the walk-forward backtest for a single symbol."""
        df_raw = fetch_historical_data(symbol, self.years)

        # reset per-symbol state
        self._open_positions = []
        self._daily_trade_counts.clear()
        symbol_trades: List[BacktestTrade] = []

        total_bars = len(df_raw)
        report_every = max(1, total_bars // 20)

        logger.info(f"🔄 Walking through {total_bars} bars for {symbol} …")

        for i in range(self.LOOKBACK, total_bars):
            window = df_raw.iloc[max(0, i - 200) : i + 1].copy()
            bar = df_raw.iloc[i]
            bar_date = str(bar.name.date()) if hasattr(bar.name, "date") else str(bar.name)

            self._total_bars_processed += 1

            # ── 1. check / exit open positions ───────────────────────────
            still_open: List[BacktestTrade] = []
            for pos in self._open_positions:
                exited = self._check_exit(pos, bar, bar_date)
                if exited:
                    symbol_trades.append(pos)
                    self._trades.append(pos)
                    self._capital += pos.pnl
                else:
                    pos.bars_held += 1
                    still_open.append(pos)
            self._open_positions = still_open

            # ── 2. compute features ──────────────────────────────────────
            df_feat = self.feature_engine.compute_all_features(window, symbol)
            if df_feat.empty or len(df_feat) < 30:
                continue

            # ── 3. evaluate strategies ───────────────────────────────────
            if (
                len(self._open_positions) < self.MAX_OPEN_POSITIONS
                and self._daily_trade_counts[bar_date] < self.MAX_DAILY_TRADES
            ):
                for strat_name, strategy in self.strategies.items():
                    # reset ORB daily
                    if strat_name == "ORB":
                        strategy.reset_daily(symbol)

                    signal = strategy.generate_signal(df_feat, symbol)

                    if signal.is_actionable and signal.confidence >= 30:
                        trade = self._open_trade(
                            symbol, strat_name, signal, bar_date
                        )
                        if trade:
                            self._open_positions.append(trade)
                            self._daily_trade_counts[bar_date] += 1

            # equity snapshot
            unrealised = sum(
                self._unrealised_pnl(p, bar) for p in self._open_positions
            )
            self._equity_curve.append(
                (bar_date, round(self._capital + unrealised, 2))
            )

            if (i - self.LOOKBACK) % report_every == 0:
                pct = (i - self.LOOKBACK) / (total_bars - self.LOOKBACK) * 100
                logger.info(
                    f"   {symbol} {pct:5.1f}% | "
                    f"Trades: {len(symbol_trades)} | "
                    f"Capital: ₹{self._capital:,.0f}"
                )

        # force-close anything still open at end
        for pos in self._open_positions:
            last_bar = df_raw.iloc[-1]
            last_date = str(last_bar.name.date()) if hasattr(last_bar.name, "date") else str(last_bar.name)
            self._force_exit(pos, last_bar, last_date, "BACKTEST_END")
            symbol_trades.append(pos)
            self._trades.append(pos)
            self._capital += pos.pnl
        self._open_positions = []

        wins = [t for t in symbol_trades if t.is_winner]
        losses = [t for t in symbol_trades if not t.is_winner and t.pnl != 0]

        logger.info(
            f"✅ {symbol} backtest done — "
            f"{len(symbol_trades)} trades, "
            f"{len(wins)} wins, {len(losses)} losses"
        )

        return {
            "symbol": symbol,
            "total_bars": total_bars,
            "trades": [asdict(t) for t in symbol_trades],
        }

    # ──────────────────────────────────────────────────────────────────────────
    #  Trade helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _open_trade(
        self, symbol: str, strat_name: str, signal, bar_date: str
    ) -> Optional[BacktestTrade]:
        """Create and register a new backtest trade from a strategy signal."""
        risk_amount = self._capital * self.position_size_pct
        if risk_amount <= 0 or signal.entry_price <= 0:
            return None

        # Options Scale Simulation at Entry
        self._trade_counter += 1
        allocated = self._capital * self.ALLOCATION
        premium = max(signal.entry_price * 0.01, 1.0)
        qty = int(allocated / premium) if allocated > 0 else 0
        
        trade = BacktestTrade(
            trade_id=self._trade_counter,
            symbol=symbol,
            strategy=strat_name,
            direction=signal.signal_type.value,
            entry_price=signal.entry_price,
            target1=signal.target1,
            target2=signal.target2,
            stop_loss=signal.stop_loss,
            confidence=signal.confidence,
            entry_date=bar_date,
            quantity=qty,
            allocated_at_entry=allocated,
        )
        return trade

    def _check_exit(
        self, trade: BacktestTrade, bar, bar_date: str
    ) -> bool:
        """Check if a trade should be closed on the current bar.
        Returns True if the trade was closed."""
        high = bar["high"]
        low = bar["low"]
        close = bar["close"]

        is_call = trade.direction == "BUY_CALL"

        # ── Stop-loss hit ────────────────────────────────────────────────
        if is_call and low <= trade.stop_loss:
            self._close_trade(trade, trade.stop_loss, bar_date, "STOPLOSS")
            return True
        if not is_call and high >= trade.stop_loss:
            self._close_trade(trade, trade.stop_loss, bar_date, "STOPLOSS")
            return True

        # ── Target-2 hit ─────────────────────────────────────────────────
        if is_call and high >= trade.target2:
            self._close_trade(trade, trade.target2, bar_date, "TARGET2")
            return True
        if not is_call and low <= trade.target2:
            self._close_trade(trade, trade.target2, bar_date, "TARGET2")
            return True

        # ── Target-1 hit (partial conceptual) ────────────────────────────
        if is_call and high >= trade.target1:
            self._close_trade(trade, trade.target1, bar_date, "TARGET1")
            return True
        if not is_call and low <= trade.target1:
            self._close_trade(trade, trade.target1, bar_date, "TARGET1")
            return True

        # ── Max holding period (5 bars) ──────────────────────────────────
        if trade.bars_held >= 5:
            self._close_trade(trade, close, bar_date, "MAX_HOLD")
            return True

        return False

    def _close_trade(
        self, trade: BacktestTrade, exit_price: float, bar_date: str, reason: str
    ):
        trade.exit_price = round(exit_price, 2)
        trade.exit_date = bar_date
        trade.exit_reason = reason

        # 1. Use the pre-calculated allocation and quantity from Entry
        qty = trade.quantity
        allocated = trade.allocated_at_entry
            
        # 4. Spot difference (How much the underlying index moved)
        if trade.direction == "BUY_CALL":
            spot_diff = exit_price - trade.entry_price
        else:
            spot_diff = trade.entry_price - exit_price
            
        # 5. Assume ~1.0 Delta (Deep ITM Option captures 100% of spot move)
        trade.pnl = round(spot_diff * 1.0 * qty, 2)
        
        # 6. Options Max Loss is limited to the premium paid (cannot lose more than allocated)
        if trade.pnl < -allocated:
            trade.pnl = -allocated

        trade.pnl_pct = round(
            trade.pnl / allocated * 100, 4
        ) if allocated > 0 else 0.0
        trade.is_winner = trade.pnl > 0

    def _force_exit(self, trade: BacktestTrade, bar, bar_date: str, reason: str):
        close = bar["close"]
        self._close_trade(trade, close, bar_date, reason)

    def _unrealised_pnl(self, trade: BacktestTrade, bar) -> float:
        close = bar["close"]
        if trade.direction == "BUY_CALL":
            spot_diff = close - trade.entry_price
        else:
            spot_diff = trade.entry_price - close
            
        qty = trade.quantity
        allocated = trade.allocated_at_entry
        
        pnl = round(spot_diff * 1.0 * qty, 2)
        if pnl < -allocated:
            pnl = -allocated
            
        return pnl

    # ──────────────────────────────────────────────────────────────────────────
    #  Report compilation
    # ──────────────────────────────────────────────────────────────────────────

    def _compile_report(self, all_results: Dict[str, Dict]) -> Dict[str, Any]:
        """Build the master analytics dictionary."""
        trades = self._trades
        pnl_list = [t.pnl for t in trades]
        wins = [t for t in trades if t.is_winner]
        losses = [t for t in trades if not t.is_winner and t.pnl != 0]
        flat = [t for t in trades if t.pnl == 0]

        total = len(trades)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total * 100) if total else 0

        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        net_pnl = sum(pnl_list)
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

        avg_win = float(np.mean([t.pnl for t in wins])) if wins else 0
        avg_loss = float(np.mean([t.pnl for t in losses])) if losses else 0
        largest_win = max((t.pnl for t in wins), default=0)
        largest_loss = min((t.pnl for t in losses), default=0)

        avg_bars_held = float(np.mean([t.bars_held for t in trades])) if trades else 0

        # expectancy
        expectancy = (
            (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)
        ) if total else 0

        # equity & drawdown
        equity = [e[1] for e in self._equity_curve]
        dates = [e[0] for e in self._equity_curve]
        max_dd, max_dd_pct = self._max_drawdown(equity)

        # Sharpe
        if len(equity) > 2:
            returns = np.diff(equity) / np.maximum(np.abs(equity[:-1]), 1e-9)
            sharpe = (
                float(np.mean(returns) / np.std(returns) * np.sqrt(252))
                if np.std(returns) > 0
                else 0
            )
            sortino = self._sortino(returns)
        else:
            sharpe = sortino = 0.0

        # per-strategy breakdown
        strat_breakdown: Dict[str, Dict] = {}
        for strat_name in self.strategies:
            st_trades = [t for t in trades if t.strategy == strat_name]
            st_wins = [t for t in st_trades if t.is_winner]
            st_losses = [t for t in st_trades if not t.is_winner and t.pnl != 0]
            strat_breakdown[strat_name] = {
                "total_trades": len(st_trades),
                "wins": len(st_wins),
                "losses": len(st_losses),
                "win_rate": round(len(st_wins) / len(st_trades) * 100, 2) if st_trades else 0,
                "net_pnl": round(sum(t.pnl for t in st_trades), 2),
                "avg_pnl": round(float(np.mean([t.pnl for t in st_trades])), 2) if st_trades else 0,
                "largest_win": round(max((t.pnl for t in st_wins), default=0), 2),
                "largest_loss": round(min((t.pnl for t in st_losses), default=0), 2),
            }

        # exit reason breakdown
        exit_reasons: Dict[str, int] = defaultdict(int)
        for t in trades:
            exit_reasons[t.exit_reason] += 1

        # monthly PnL
        monthly_pnl: Dict[str, float] = defaultdict(float)
        for t in trades:
            if t.exit_date:
                month_key = t.exit_date[:7]  # "YYYY-MM"
                monthly_pnl[month_key] += t.pnl

        # yearly PnL
        yearly_pnl: Dict[str, float] = defaultdict(float)
        for t in trades:
            if t.exit_date:
                year_key = t.exit_date[:4]
                yearly_pnl[year_key] += t.pnl

        # consecutive runs
        max_consec_wins = self._max_consecutive(trades, True)
        max_consec_losses = self._max_consecutive(trades, False)

        return {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "symbols": self.symbols,
                "years": self.years,
                "initial_capital": self.initial_capital,
                "total_bars_processed": self._total_bars_processed,
            },
            "summary": {
                "total_trades": total,
                "winning_trades": win_count,
                "losing_trades": loss_count,
                "flat_trades": len(flat),
                "win_rate": round(win_rate, 2),
                "net_pnl": round(net_pnl, 2),
                "gross_profit": round(gross_profit, 2),
                "gross_loss": round(gross_loss, 2),
                "profit_factor": round(profit_factor, 2),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "largest_win": round(largest_win, 2),
                "largest_loss": round(largest_loss, 2),
                "expectancy": round(expectancy, 2),
                "avg_bars_held": round(avg_bars_held, 2),
                "max_drawdown": round(max_dd, 2),
                "max_drawdown_pct": round(max_dd_pct, 2),
                "sharpe_ratio": round(sharpe, 2),
                "sortino_ratio": round(sortino, 2),
                "max_consecutive_wins": max_consec_wins,
                "max_consecutive_losses": max_consec_losses,
                "final_capital": round(self._capital, 2),
                "total_return_pct": round(
                    (self._capital - self.initial_capital)
                    / self.initial_capital
                    * 100,
                    2,
                ),
            },
            "strategy_breakdown": strat_breakdown,
            "exit_reason_breakdown": dict(exit_reasons),
            "monthly_pnl": dict(sorted(monthly_pnl.items())),
            "yearly_pnl": dict(sorted(yearly_pnl.items())),
            "equity_curve": {
                "dates": dates[::max(1, len(dates)//500)],   # downsample for JSON
                "values": [round(v, 2) for v in equity[::max(1, len(equity)//500)]],
            },
            "trades": [asdict(t) for t in trades],
        }

    # ──────────────────────────────────────────────────────────────────────────
    #  Math helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _max_drawdown(equity: List[float]) -> Tuple[float, float]:
        if not equity:
            return 0.0, 0.0
        peak = equity[0]
        max_dd = 0.0
        for v in equity:
            if v > peak:
                peak = v
            dd = peak - v
            if dd > max_dd:
                max_dd = dd
        max_dd_pct = (max_dd / peak * 100) if peak > 0 else 0.0
        return max_dd, max_dd_pct

    @staticmethod
    def _sortino(returns: np.ndarray) -> float:
        downside = returns[returns < 0]
        if len(downside) == 0 or np.std(downside) == 0:
            return 0.0
        return float(np.mean(returns) / np.std(downside) * np.sqrt(252))

    @staticmethod
    def _max_consecutive(trades: List[BacktestTrade], wins: bool) -> int:
        best = 0
        streak = 0
        for t in trades:
            if (wins and t.is_winner) or (not wins and not t.is_winner and t.pnl != 0):
                streak += 1
                best = max(best, streak)
            else:
                streak = 0
        return best

    # ──────────────────────────────────────────────────────────────────────────
    #  Console pretty-print
    # ──────────────────────────────────────────────────────────────────────────

    def _print_summary(self, report: Dict):
        s = report["summary"]
        sb = report["strategy_breakdown"]

        print("\n" + "═" * 70)
        print("  📊  BACKTEST RESULTS")
        print("═" * 70)
        print(f"  Period          : last {report['meta']['years']} years")
        print(f"  Symbols         : {', '.join(report['meta']['symbols'])}")
        print(f"  Initial Capital : ₹{report['meta']['initial_capital']:,.0f}")
        print(f"  Final Capital   : ₹{s['final_capital']:,.0f}")
        print(f"  Total Return    : {s['total_return_pct']:+.2f}%")
        print("─" * 70)
        print(f"  Total Trades    : {s['total_trades']}")
        print(f"  Win / Loss      : {s['winning_trades']} / {s['losing_trades']}")
        print(f"  Win Rate        : {s['win_rate']:.2f}%")
        print(f"  Net P&L         : ₹{s['net_pnl']:,.2f}")
        print(f"  Gross Profit    : ₹{s['gross_profit']:,.2f}")
        print(f"  Gross Loss      : ₹{s['gross_loss']:,.2f}")
        print(f"  Profit Factor   : {s['profit_factor']:.2f}")
        print(f"  Expectancy      : ₹{s['expectancy']:,.2f}")
        print("─" * 70)
        print(f"  Avg Win         : ₹{s['avg_win']:,.2f}")
        print(f"  Avg Loss        : ₹{s['avg_loss']:,.2f}")
        print(f"  Largest Win     : ₹{s['largest_win']:,.2f}")
        print(f"  Largest Loss    : ₹{s['largest_loss']:,.2f}")
        print(f"  Avg Bars Held   : {s['avg_bars_held']:.1f}")
        print("─" * 70)
        print(f"  Max Drawdown    : ₹{s['max_drawdown']:,.2f} ({s['max_drawdown_pct']:.2f}%)")
        print(f"  Sharpe Ratio    : {s['sharpe_ratio']:.2f}")
        print(f"  Sortino Ratio   : {s['sortino_ratio']:.2f}")
        print(f"  Max Consec Wins : {s['max_consecutive_wins']}")
        print(f"  Max Consec Loss : {s['max_consecutive_losses']}")
        print("─" * 70)

        print("\n  📈 Strategy Breakdown:")
        for name, data in sb.items():
            print(
                f"    {name:18s} │ Trades: {data['total_trades']:4d} │ "
                f"WR: {data['win_rate']:5.1f}% │ "
                f"P&L: ₹{data['net_pnl']:>10,.2f}"
            )

        print("\n  📅 Exit Reasons:")
        for reason, count in report["exit_reason_breakdown"].items():
            print(f"    {reason:18s} │ {count}")

        print("\n  📆 Yearly P&L:")
        for year, pnl in report["yearly_pnl"].items():
            bar = "█" * max(1, int(abs(pnl) / max(1, max(abs(v) for v in report["yearly_pnl"].values())) * 30))
            sign = "🟢" if pnl >= 0 else "🔴"
            print(f"    {year}  {sign} ₹{pnl:>10,.2f}  {bar}")

        print("═" * 70 + "\n")
