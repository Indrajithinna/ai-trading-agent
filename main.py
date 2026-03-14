"""
Main Entry Point - Autonomous AI Trading Agent Platform
========================================================
Orchestrates all 19 modules into a unified trading system.
Runs in Paper Trading mode by default.
"""

import os
import sys
import time
import signal
import threading
from datetime import datetime

# Ensure package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_trading_agent.config import load_config, MasterConfig
from ai_trading_agent.utils.logger import get_logger
from ai_trading_agent.utils.helpers import (
    get_ist_now, is_market_hours, is_square_off_time, 
    is_trading_day, format_currency, format_signal_message
)

# Agents
from ai_trading_agent.agents.market_data_agent import MarketDataAgent
from ai_trading_agent.agents.scanner_agent import MarketScannerAgent
from ai_trading_agent.agents.feature_engineering_agent import FeatureEngineeringAgent
from ai_trading_agent.agents.regime_detector import MarketRegimeDetector
from ai_trading_agent.agents.multi_timeframe_engine import MultiTimeframeEngine
from ai_trading_agent.agents.signal_aggregator import (
    SignalAggregator, TradeScoreEngine, SmartStrikeSelector, AggregatedSignal
)

# Strategies
from ai_trading_agent.strategies.vwap_strategy import VWAPBreakoutStrategy
from ai_trading_agent.strategies.ema_strategy import EMAMomentumStrategy
from ai_trading_agent.strategies.orb_strategy import ORBStrategy

# Models
from ai_trading_agent.models.ai_prediction_model import AIPredictionModel
from ai_trading_agent.models.reinforcement_learning_agent import RLTradingAgent

# Risk & Execution
from ai_trading_agent.risk.risk_manager import RiskManager
from ai_trading_agent.execution.paper_trader import PaperTradingEngine
from ai_trading_agent.execution.performance_analyzer import PerformanceAnalyzer

# Signals
from ai_trading_agent.signals.telegram_alert import TelegramAlertSystem

# Scheduler
from ai_trading_agent.scheduler.market_scheduler import MarketScheduler

logger = get_logger("MainOrchestrator")


class TradingOrchestrator:
    """
    Central orchestrator that coordinates all trading agents and modules.
    
    Workflow per tick:
    1. Market Data Agent fetches latest data
    2. Feature Engineering computes indicators
    3. Market Scanner identifies opportunities
    4. Regime Detector classifies market conditions
    5. Multi-Timeframe Engine checks alignment
    6. Strategy Agents generate signals (parallel)
    7. AI Prediction Model gives probability
    8. RL Agent provides recommendation
    9. Signal Aggregator checks consensus
    10. Trade Score Engine computes composite score
    11. Smart Strike Selector picks optimal strike
    12. Risk Manager validates the trade
    13. Paper Trader executes the trade
    14. Telegram sends alert
    15. Performance Analyzer records the trade
    """
    
    def __init__(self):
        self.config = load_config()
        self._running = False
        self._initialized = False
        
        logger.info("="*60)
        logger.info("🤖 AUTONOMOUS AI TRADING AGENT PLATFORM")
        logger.info(f"📅 Date: {get_ist_now().strftime('%d-%b-%Y')}")
        logger.info(f"💰 Capital: {format_currency(self.config.trading.initial_capital)}")
        logger.info(f"📄 Mode: {self.config.execution_mode.upper()}")
        logger.info("="*60)
    
    def initialize(self):
        """Initialize all modules and agents."""
        logger.info("🔄 Initializing all modules...")
        
        # ─── Module 1: Market Data Agent ─────────────────────
        self.market_data = MarketDataAgent(self.config.flattrade, self.config.market)
        self.market_data.authenticate()
        
        # ─── Module 3: Feature Engineering ───────────────────
        self.feature_engine = FeatureEngineeringAgent()
        
        # ─── Module 2: Market Scanner ────────────────────────
        self.scanner = MarketScannerAgent(self.market_data, self.config.strategy)
        
        # ─── Module 4: Regime Detection ──────────────────────
        self.regime_detector = MarketRegimeDetector(self.config.strategy)
        
        # ─── Module 5: Multi-Timeframe Engine ────────────────
        self.mtf_engine = MultiTimeframeEngine(self.market_data, self.feature_engine)
        
        # ─── Module 6: Strategy Agents ───────────────────────
        self.strategies = {
            "VWAP": VWAPBreakoutStrategy(self.config.strategy),
            "EMA": EMAMomentumStrategy(self.config.strategy),
            "ORB": ORBStrategy(self.config.strategy),
        }
        
        # ─── Module 7: AI Prediction Model ───────────────────
        self.ai_model = AIPredictionModel(self.config.ai_model)
        
        # ─── Module 8: RL Agent ──────────────────────────────
        self.rl_agent = RLTradingAgent(self.config.rl)
        self.rl_agent.load()
        
        # ─── Module 9: Signal Aggregator ─────────────────────
        self.signal_aggregator = SignalAggregator(self.config.trading)
        
        # ─── Module 10: Trade Score Engine ───────────────────
        self.score_engine = TradeScoreEngine(self.config.trading)
        
        # ─── Module 11: Strike Selector ──────────────────────
        self.strike_selector = SmartStrikeSelector(self.config.trading)
        
        # ─── Module 12: Risk Manager ─────────────────────────
        self.risk_manager = RiskManager(self.config.trading)
        
        # ─── Module 13: Telegram Alerts ──────────────────────
        self.telegram = TelegramAlertSystem(self.config.telegram)
        
        # ─── Module 14: Paper Trader ─────────────────────────
        self.paper_trader = PaperTradingEngine(self.config.trading, self.risk_manager)
        self.paper_trader.load_state()
        
        # ─── Module 15: Performance Analyzer ─────────────────
        self.performance = PerformanceAnalyzer()
        
        # ─── Module 17: Market Scheduler ─────────────────────
        self.scheduler = MarketScheduler()
        self._register_scheduler_callbacks()
        
        self._initialized = True
        logger.info("✅ All 19 modules initialized successfully!")
        
        # Send startup notification
        self.telegram.send_system_alert(
            "start",
            f"🤖 AI Trading Agent Started\n\n"
            f"Mode: {self.config.execution_mode.upper()}\n"
            f"Capital: {format_currency(self.config.trading.initial_capital)}\n"
            f"Markets: {', '.join(self.config.market.markets)}\n"
            f"Strategies: VWAP, EMA, ORB + AI/RL"
        )
    
    def _register_scheduler_callbacks(self):
        """Register callbacks for market events."""
        self.scheduler.register_callback("pre_market", self._on_pre_market)
        self.scheduler.register_callback("market_open", self._on_market_open)
        self.scheduler.register_callback("orb_complete", self._on_orb_complete)
        self.scheduler.register_callback("trading_tick", self._on_trading_tick)
        self.scheduler.register_callback("square_off", self._on_square_off)
        self.scheduler.register_callback("daily_summary", self._on_daily_summary)
    
    def _on_pre_market(self):
        """Pre-market preparation at 9:00 AM."""
        logger.info("🌅 Pre-market preparation starting...")
        
        # Train AI model if needed
        for symbol in self.config.market.markets:
            df = self.market_data.get_ohlc_data(symbol, 15, 200)
            if not df.empty:
                df_features = self.feature_engine.compute_all_features(df, symbol)
                self.ai_model.train(df_features)
                break  # Train once on available data
    
    def _on_market_open(self):
        """Market open at 9:15 AM."""
        logger.info("🔔 Market opened! Starting data collection...")
        self.market_data.start_streaming()
        
        # Reset ORB strategy for new day
        for symbol in self.config.market.markets:
            self.strategies["ORB"].reset_daily(symbol)
    
    def _on_orb_complete(self):
        """ORB period complete at 9:30 AM."""
        logger.info("📏 ORB period complete. Setting opening range...")
        
        for symbol in self.config.market.markets:
            df_15m = self.market_data.get_ohlc_data(symbol, 15, 2)
            if not df_15m.empty:
                first_bar = df_15m.iloc[0]
                self.strategies["ORB"].set_opening_range(
                    symbol, first_bar['high'], first_bar['low']
                )
    
    def _on_trading_tick(self):
        """Called every tick during trading hours."""
        try:
            self._process_trading_cycle()
        except Exception as e:
            logger.error(f"❌ Trading cycle error: {e}", exc_info=True)
    
    def _on_square_off(self):
        """Square off all positions at 3:20 PM."""
        logger.info("📤 Square off time! Closing all positions...")
        self.paper_trader.square_off_all("EOD_SQUARE_OFF")
        self.telegram.send_system_alert("info", "📤 All positions squared off for the day.")
    
    def _on_daily_summary(self):
        """Generate and send daily summary at 3:30 PM."""
        logger.info("📋 Generating daily summary...")
        
        risk_status = self.risk_manager.get_risk_status()
        portfolio = self.paper_trader.get_portfolio_status()
        perf = self.performance.get_summary()
        
        summary = {
            **risk_status,
            **portfolio,
            "signals_generated": self._signals_generated if hasattr(self, '_signals_generated') else 0,
            "signals_executed": self._signals_executed if hasattr(self, '_signals_executed') else 0,
            "ai_accuracy": perf.get('win_rate', 0),
        }
        
        self.telegram.send_daily_summary(summary)
        self.performance.save_report()
        self.paper_trader.save_state()
        self.rl_agent.save()
        
        self.market_data.stop_streaming()
        logger.info("📋 Daily summary sent. Market closed.")
    
    def _process_trading_cycle(self):
        """
        Main trading logic executed every tick.
        
        This is the heart of the system — coordinating all 19 modules.
        """
        if not hasattr(self, '_signals_generated'):
            self._signals_generated = 0
            self._signals_executed = 0
        
        # Pre-check: Is trading allowed?
        risk_check = self.risk_manager.check_trade_allowed()
        if not risk_check['allowed']:
            return
        
        for symbol in self.config.market.markets:
            try:
                self._analyze_and_trade(symbol)
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
    
    def _analyze_and_trade(self, symbol: str):
        """Full analysis and trading pipeline for a single symbol."""
        
        # ─── Step 1: Get Market Data ─────────────────────────
        df_5m = self.market_data.get_ohlc_data(symbol, 5, 100)
        if df_5m.empty:
            return
        
        spot_price = self.market_data.get_spot_price(symbol)
        
        # ─── Step 2: Feature Engineering ─────────────────────
        df_features = self.feature_engine.compute_all_features(df_5m, symbol)
        if df_features.empty:
            return
        
        # ─── Step 3: Market Regime Detection ─────────────────
        regime_info = self.regime_detector.detect_regime(df_features, symbol)
        
        # ─── Step 4: Multi-Timeframe Analysis ────────────────
        mtf_result = self.mtf_engine.analyze(symbol)
        
        if not mtf_result.trade_allowed:
            return  # Timeframes not aligned
        
        # ─── Step 5: Run Strategy Agents (parallel signals) ──
        strategy_signals = []
        for name, strategy in self.strategies.items():
            signal = strategy.generate_signal(df_features, symbol)
            strategy_signals.append(signal)
        
        # ─── Step 6: AI Prediction ───────────────────────────
        ai_prediction = self.ai_model.predict(df_features)
        
        # ─── Step 7: RL Recommendation ───────────────────────
        latest_features = self.feature_engine.get_latest_features(symbol)
        if latest_features:
            rl_state = {
                'rsi': latest_features.get('RSI', 50),
                'macd': latest_features.get('MACD_Hist', 0),
                'ema_diff': latest_features.get('EMA_Diff', 0),
                'vwap_diff': latest_features.get('VWAP_Diff', 0),
                'atr': latest_features.get('ATR', 0),
                'volume_ratio': latest_features.get('Volume_Ratio', 1),
                'trend_strength': latest_features.get('Trend_Strength', 0),
                'volatility': latest_features.get('ATR_Pct', 0),
                'position_status': 0,
                'unrealized_pnl': 0
            }
            rl_prediction = self.rl_agent.predict(rl_state)
        else:
            rl_prediction = {"action": "HOLD", "confidence": 0}
        
        # ─── Step 8: Signal Aggregation & Consensus ──────────
        aggregation = self.signal_aggregator.aggregate(strategy_signals, symbol)
        
        if not aggregation or not aggregation.get('consensus_met'):
            return  # No consensus
        
        self._signals_generated += 1
        
        # ─── Step 9: Trade Score ─────────────────────────────
        trade_score = self.score_engine.compute_score(
            aggregation=aggregation,
            regime_info=regime_info,
            mtf_result=mtf_result,
            ai_prediction=ai_prediction,
            features=latest_features
        )
        
        # Minimum score check
        if trade_score < self.config.trading.min_trade_score:
            logger.info(f"❌ {symbol} score {trade_score:.0f} < {self.config.trading.min_trade_score}. Skipping.")
            return
        
        # AI probability check
        if ai_prediction.get('probability', 0) < self.config.trading.min_ai_probability:
            if ai_prediction.get('prediction') != aggregation.get('direction'):
                logger.info(f"❌ {symbol} AI disagrees. Skipping.")
                return
        
        # ─── Step 10: Strike Selection ───────────────────────
        direction = aggregation['direction']
        option_chain = self.market_data.get_option_chain(symbol)
        
        strike_info = self.strike_selector.select_strike(
            symbol=symbol,
            spot_price=spot_price,
            direction=direction,
            confidence=trade_score,
            option_chain=option_chain
        )
        
        # ─── Step 11: Build Final Signal ─────────────────────
        final_signal = {
            'symbol': symbol,
            'strike': strike_info['strike'],
            'option_type': strike_info['option_type'],
            'direction': direction,
            'entry_price': strike_info['entry_price'],
            'target1': strike_info['target1'],
            'target2': strike_info['target2'],
            'stop_loss': strike_info['stop_loss'],
            'trade_score': trade_score,
            'ai_confidence': ai_prediction.get('confidence', 0),
            'confirming_agents': aggregation['confirming_count'],
            'total_agents': aggregation['total_agents'],
            'market_regime': regime_info.regime.value,
            'spot_price': spot_price,
        }
        
        # ─── Step 12: Execute Trade ──────────────────────────
        position = self.paper_trader.execute_signal(final_signal)
        
        if position:
            self._signals_executed += 1
            
            # ─── Step 13: Send Telegram Alert ────────────────
            self.telegram.send_trade_signal(final_signal)
            
            # ─── Step 14: Record for Performance ─────────────
            self.performance.record_trade({
                'symbol': symbol,
                'strike': strike_info['strike'],
                'option_type': strike_info['option_type'],
                'direction': direction,
                'entry_price': strike_info['entry_price'],
                'trade_score': trade_score,
                'strategy': ', '.join(aggregation['confirming_strategies']),
                'pnl': 0,  # Updated when position closes
            })
            
            logger.info(
                f"🎉 TRADE EXECUTED: {symbol} {strike_info['strike']} "
                f"{strike_info['option_type']} | Score: {trade_score:.0f}"
            )
    
    def start(self):
        """Start the trading system."""
        if not self._initialized:
            self.initialize()
        
        self._running = True
        
        logger.info("🚀 Trading system starting...")
        
        # Start scheduler (handles all timing)
        self.scheduler.start()
        
        # For immediate testing/demo: run one full cycle  
        if not is_market_hours():
            logger.info("📅 Market is currently closed. Running demo cycle...")
            self._run_demo_cycle()
        
        # Keep running
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def _run_demo_cycle(self):
        """Run a demo cycle for testing outside market hours."""
        logger.info("🎭 Running demo trading cycle...")
        
        # Start simulated data
        self.market_data.start_streaming()
        time.sleep(2)  # Let some data accumulate
        
        # Process one cycle for each symbol
        for symbol in self.config.market.markets:
            try:
                self._analyze_and_trade(symbol)
            except Exception as e:
                logger.error(f"Demo cycle error for {symbol}: {e}")
        
        # Update positions
        self.paper_trader.update_positions({})
        
        # Show status
        portfolio = self.paper_trader.get_portfolio_status()
        risk = self.risk_manager.get_risk_status()
        
        logger.info(f"📊 Portfolio: {portfolio}")
        logger.info(f"🛡️ Risk: {risk}")
        
        self.market_data.stop_streaming()
        logger.info("🎭 Demo cycle complete!")
    
    def stop(self):
        """Stop the trading system gracefully."""
        logger.info("⏹️ Stopping trading system...")
        self._running = False
        
        # Square off any open positions
        self.paper_trader.square_off_all("SYSTEM_SHUTDOWN")
        
        # Save state
        self.paper_trader.save_state()
        self.rl_agent.save()
        self.performance.save_report()
        
        # Stop components
        self.scheduler.stop()
        self.market_data.stop_streaming()
        
        # Send shutdown notification
        self.telegram.send_system_alert("stop", "🤖 AI Trading Agent has been stopped.")
        
        logger.info("✅ Trading system stopped gracefully.")
    
    def get_system_status(self) -> dict:
        """Get comprehensive system status."""
        return {
            "running": self._running,
            "initialized": self._initialized,
            "mode": self.config.execution_mode,
            "risk": self.risk_manager.get_risk_status() if self._initialized else {},
            "portfolio": self.paper_trader.get_portfolio_status() if self._initialized else {},
            "performance": self.performance.get_summary() if self._initialized else {},
            "scheduler": self.scheduler.get_status() if self._initialized else {},
            "signals_generated": getattr(self, '_signals_generated', 0),
            "signals_executed": getattr(self, '_signals_executed', 0),
        }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Trading Agent Platform")
    parser.add_argument("--mode", choices=["trade", "dashboard", "demo", "backtest"], 
                       default="demo", help="Run mode")
    parser.add_argument("--dashboard-only", action="store_true",
                       help="Launch only the dashboard")
    parser.add_argument("--years", type=float, default=1.0,
                       help="Years of historical data for backtest (0.1 - 10)")
    parser.add_argument("--symbol", type=str, default="",
                       help="Comma-separated symbols to backtest (default: all)")
    parser.add_argument("--capital", type=float, default=100000.0,
                       help="Initial capital for backtest")
    
    args = parser.parse_args()
    
    if args.mode == "dashboard" or args.dashboard_only:
        print("🖥️ Launching dashboard...")
        print("Run: streamlit run ai_trading_agent/dashboard/app.py")
        os.system(f"streamlit run {os.path.join(os.path.dirname(__file__), 'dashboard', 'app.py')}")
    elif args.mode == "backtest":
        from ai_trading_agent.execution.backtester import BacktestEngine
        symbols = [s.strip().upper() for s in args.symbol.split(",") if s.strip()] or None
        engine = BacktestEngine(
            symbols=symbols,
            years=args.years,
            initial_capital=args.capital,
        )
        report = engine.run()
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        html_path = os.path.join(data_dir, "backtest_report.html")
        if os.path.exists(html_path):
            print(f"\n🌐 Open the HTML report in your browser:")
            print(f"   {os.path.abspath(html_path)}")
    elif args.mode == "trade":
        orchestrator = TradingOrchestrator()
        orchestrator.start()
    else:  # demo
        orchestrator = TradingOrchestrator()
        orchestrator.initialize()
        orchestrator._run_demo_cycle()
        
        # Print status
        status = orchestrator.get_system_status()
        print("\n" + "="*60)
        print("📊 SYSTEM STATUS")
        print("="*60)
        print(f"Mode: {status['mode']}")
        print(f"Signals Generated: {status['signals_generated']}")
        print(f"Signals Executed: {status['signals_executed']}")
        
        if status.get('risk'):
            print(f"\n🛡️ Risk Status:")
            print(f"  Capital: {format_currency(status['risk'].get('capital', 0))}")
            print(f"  Daily P&L: {format_currency(status['risk'].get('daily_pnl', 0))}")
            print(f"  Trades: {status['risk'].get('total_trades', 0)}/{status['risk'].get('total_trades', 0) + status['risk'].get('trades_remaining', 0)}")
            print(f"  Win Rate: {status['risk'].get('win_rate', 0)}%")
        
        print("="*60)
        print("✅ Demo complete! System is ready for paper trading.")
        print("\nTo start trading: python -m ai_trading_agent.main --mode trade")
        print("To view dashboard: python -m ai_trading_agent.main --mode dashboard")
        
        orchestrator.stop()


if __name__ == "__main__":
    main()
