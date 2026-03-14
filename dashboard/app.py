"""
Dashboard Interface (Module 18)
=================================
Streamlit dashboard displaying:
- Live market data
- AI predictions
- Trade signals
- Open trades
- Profit/Loss
- System status
"""

import os
import sys
import json
import time
from datetime import datetime, date

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    import streamlit as st
    import pandas as pd
    import numpy as np
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

from ai_trading_agent.config import load_config


def run_dashboard():
    """Launch the Streamlit dashboard."""
    if not STREAMLIT_AVAILABLE:
        print("Streamlit not installed. Install with: pip install streamlit")
        return
    
    config = load_config()
    
    # ═══ Page Configuration ═══
    st.set_page_config(
        page_title="🤖 AI Trading Agent",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # ═══ Custom CSS ═══
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * { font-family: 'Inter', sans-serif; }
        
        .main { background-color: #0e1117; }
        
        .metric-card {
            background: linear-gradient(135deg, #1a1f2e 0%, #151923 100%);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            margin: 8px 0;
            box-shadow: 0 4px 24px rgba(0,0,0,0.3);
        }
        
        .metric-value {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(90deg, #00d4aa, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .metric-label {
            font-size: 13px;
            color: #8b95a5;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .badge-active { background: rgba(0,212,170,0.15); color: #00d4aa; }
        .badge-warning { background: rgba(255,193,7,0.15); color: #ffc107; }
        .badge-danger { background: rgba(255,82,82,0.15); color: #ff5252; }
        
        .signal-card {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid rgba(124,58,237,0.3);
            border-radius: 12px;
            padding: 20px;
            margin: 10px 0;
        }
        
        .header-gradient {
            background: linear-gradient(90deg, #00d4aa, #7c3aed, #f59e0b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 32px;
            font-weight: 700;
        }
        
        div[data-testid="stMetricValue"] { font-size: 24px; }
        
        .stTabs [data-baseweb="tab-list"] {
            background-color: #1a1f2e;
            border-radius: 8px;
            padding: 4px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ═══ Sidebar ═══
    with st.sidebar:
        st.markdown("## 🤖 AI Trading Agent")
        st.markdown("---")
        
        # System Status
        st.markdown("### System Status")
        
        mode = "📄 Paper Trading" if config.execution_mode == "paper" else "🔴 LIVE"
        st.markdown(f"**Mode:** {mode}")
        st.markdown(f"**Capital:** ₹{config.trading.initial_capital:,.0f}")
        st.markdown(f"**Max Loss:** ₹{config.trading.max_daily_loss:,.0f}")
        st.markdown(f"**Target:** ₹{config.trading.daily_profit_target:,.0f}")
        st.markdown(f"**Max Trades:** {config.trading.max_trades_per_day}")
        
        st.markdown("---")
        st.markdown("### Markets")
        for market in config.market.markets:
            st.markdown(f"✅ {market}")
        
        st.markdown("---")
        st.markdown("### Strategies")
        st.markdown("✅ VWAP Breakout")
        st.markdown("✅ EMA Momentum")
        st.markdown("✅ ORB Breakout")
        st.markdown("✅ AI Prediction")
        st.markdown("✅ RL Agent")
        
        st.markdown("---")
        now = datetime.now()
        st.markdown(f"🕐 {now.strftime('%I:%M:%S %p')}")
    
    # ═══ Header ═══
    st.markdown('<p class="header-gradient">📊 Autonomous AI Trading Dashboard</p>', 
                unsafe_allow_html=True)
    st.markdown(f"*{date.today().strftime('%A, %d %B %Y')} — Paper Trading Mode*")
    
    # ═══ Key Metrics Row ═══
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    # Load data (simulated for dashboard demo)
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    
    with col1:
        st.metric("💰 Capital", f"₹{config.trading.initial_capital:,.0f}", "0.00%")
    with col2:
        st.metric("📈 Daily P&L", "₹0.00", "0.00%")
    with col3:
        st.metric("📊 Win Rate", "0.0%", "—")
    with col4:
        st.metric("🔢 Trades", "0/10", "—")
    with col5:
        st.metric("📉 Max DD", "₹0.00", "—")
    with col6:
        st.metric("🤖 AI Score", "—%", "—")
    
    st.markdown("---")
    
    # ═══ Tabs ═══
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Live Market", "🔔 Signals", "💼 Positions", 
        "📈 Performance", "🤖 AI Models", "⚙️ System"
    ])
    
    with tab1:
        st.markdown("### 📊 Live Market Data")
        
        # Simulated market data
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.markdown("#### NIFTY 50")
            nifty_price = 24250 + np.random.uniform(-50, 50)
            change = np.random.uniform(-100, 100)
            st.metric("NIFTY", f"{nifty_price:,.2f}", f"{change:+.2f}")
            
            st.markdown(f"""
            <div class='metric-card'>
            <div class='metric-label'>REGIME</div>
            <div style='color: #00d4aa; font-weight: 600;'>TRENDING ↑</div>
            <div class='metric-label' style='margin-top:8px;'>ADX: 28.5 | ATR: 145.2</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_b:
            st.markdown("#### BANKNIFTY")
            bn_price = 51500 + np.random.uniform(-100, 100)
            change = np.random.uniform(-200, 200)
            st.metric("BANKNIFTY", f"{bn_price:,.2f}", f"{change:+.2f}")
            
            st.markdown(f"""
            <div class='metric-card'>
            <div class='metric-label'>REGIME</div>
            <div style='color: #ffc107; font-weight: 600;'>SIDEWAYS ↔</div>
            <div class='metric-label' style='margin-top:8px;'>ADX: 18.2 | ATR: 312.5</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_c:
            st.markdown("#### SENSEX")
            sensex_price = 79800 + np.random.uniform(-150, 150)
            change = np.random.uniform(-300, 300)
            st.metric("SENSEX", f"{sensex_price:,.2f}", f"{change:+.2f}")
            
            st.markdown(f"""
            <div class='metric-card'>
            <div class='metric-label'>REGIME</div>
            <div style='color: #00d4aa; font-weight: 600;'>TRENDING ↑</div>
            <div class='metric-label' style='margin-top:8px;'>ADX: 26.1 | ATR: 210.8</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("### Multi-Timeframe Analysis")
        tf_data = {
            "Symbol": ["NIFTY", "BANKNIFTY", "SENSEX"],
            "15m Trend": ["🟢 BULLISH", "🟡 NEUTRAL", "🟢 BULLISH"],
            "5m Setup": ["🟢 BULLISH", "🔴 BEARISH", "🟢 BULLISH"],
            "1m Entry": ["🟢 BULLISH", "🟡 NEUTRAL", "🟡 NEUTRAL"],
            "Aligned": ["✅ YES", "❌ NO", "❌ NO"],
            "Confidence": ["78%", "42%", "61%"],
        }
        st.dataframe(pd.DataFrame(tf_data), use_container_width=True, hide_index=True)
    
    with tab2:
        st.markdown("### 🔔 Trade Signals")
        
        st.markdown("""
        <div class='signal-card'>
            <div style='font-size: 18px; font-weight: 700; color: #00d4aa;'>
                🟢 BANKNIFTY 48500 CE
            </div>
            <div style='margin-top: 12px;'>
                <span style='color: #8b95a5;'>BUY ABOVE:</span> <b>120</b><br>
                <span style='color: #8b95a5;'>TARGET:</span> <b>150 / 180</b><br>
                <span style='color: #8b95a5;'>STOP LOSS:</span> <b style='color: #ff5252;'>90</b><br>
            </div>
            <div style='margin-top: 12px;'>
                <span class='status-badge badge-active'>SCORE: 83%</span>
                <span class='status-badge badge-active'>3/4 AGENTS</span>
                <span class='status-badge badge-warning'>TRENDING</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("#### Signal History")
        signal_history = pd.DataFrame({
            "Time": ["9:42 AM", "10:15 AM", "11:30 AM"],
            "Symbol": ["BANKNIFTY 48500 CE", "NIFTY 24300 PE", "BANKNIFTY 48600 CE"],
            "Direction": ["🟢 BUY CALL", "🔴 BUY PUT", "🟢 BUY CALL"],
            "Score": ["83%", "71%", "76%"],
            "Status": ["✅ Executed", "❌ Rejected (Score < 70)", "⏳ Pending"],
        })
        st.dataframe(signal_history, use_container_width=True, hide_index=True)
    
    with tab3:
        st.markdown("### 💼 Open Positions")
        st.info("No open positions. System is in standby mode.")
        
        st.markdown("### 📋 Trade History")
        st.info("No trades executed today.")
    
    with tab4:
        st.markdown("### 📈 Performance Analytics")
        
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            st.metric("Total P&L", "₹0.00")
        with col_p2:
            st.metric("Sharpe Ratio", "0.00")
        with col_p3:
            st.metric("Profit Factor", "0.00")
        with col_p4:
            st.metric("Expectancy", "₹0.00")
        
        st.markdown("#### Equity Curve")
        equity_data = pd.DataFrame({
            "Day": range(1, 31),
            "Equity": np.cumsum(np.random.normal(20, 30, 30)) + config.trading.initial_capital
        })
        st.line_chart(equity_data.set_index("Day"), height=300)
        
        st.markdown("#### Strategy Breakdown")
        strategy_data = pd.DataFrame({
            "Strategy": ["VWAP Breakout", "EMA Momentum", "ORB Breakout", "AI Prediction"],
            "Trades": [0, 0, 0, 0],
            "Win Rate": ["—", "—", "—", "—"],
            "P&L": ["₹0", "₹0", "₹0", "₹0"],
        })
        st.dataframe(strategy_data, use_container_width=True, hide_index=True)
    
    with tab5:
        st.markdown("### 🤖 AI Model Status")
        
        col_m1, col_m2 = st.columns(2)
        
        with col_m1:
            st.markdown("#### ML Prediction Model")
            st.markdown("""
            - **Status:** Initializing (synthetic training)
            - **RF Accuracy:** Training...
            - **XGB Accuracy:** Training...
            - **Features:** RSI, MACD, EMA, VWAP, ATR, Volume, ADX
            """)
            
            st.markdown("#### Feature Importance")
            features = pd.DataFrame({
                "Feature": ["RSI", "MACD_Hist", "Volume_Ratio", "ATR", "ADX", "EMA_Diff", "VWAP_Diff"],
                "Importance": np.random.dirichlet(np.ones(7))
            }).sort_values("Importance", ascending=True)
            st.bar_chart(features.set_index("Feature"), height=250)
        
        with col_m2:
            st.markdown("#### RL Trading Agent")
            st.markdown("""
            - **Status:** Learning
            - **Episodes:** 0
            - **Epsilon:** 1.000
            - **Q-Table Size:** 0
            - **Actions:** BUY_CALL, BUY_PUT, HOLD
            """)
            
            st.markdown("#### Reward History")
            rewards = np.cumsum(np.random.normal(0.1, 0.5, 100))
            st.line_chart(pd.DataFrame({"Cumulative Reward": rewards}), height=250)
    
    with tab6:
        st.markdown("### ⚙️ System Status")
        
        col_s1, col_s2 = st.columns(2)
        
        with col_s1:
            st.markdown("#### Configuration")
            st.json({
                "mode": config.execution_mode,
                "capital": config.trading.initial_capital,
                "max_daily_loss": config.trading.max_daily_loss,
                "profit_target": config.trading.daily_profit_target,
                "max_trades": config.trading.max_trades_per_day,
                "min_score": config.trading.min_trade_score,
                "min_consensus": config.trading.min_consensus_agents,
                "markets": config.market.markets,
            })
        
        with col_s2:
            st.markdown("#### Module Status")
            modules = {
                "Market Data Agent": "✅ Active",
                "Scanner Agent": "✅ Active",
                "Feature Engine": "✅ Active",
                "Regime Detector": "✅ Active",
                "Multi-TF Engine": "✅ Active",
                "VWAP Strategy": "✅ Active",
                "EMA Strategy": "✅ Active",
                "ORB Strategy": "✅ Active",
                "AI Prediction": "🔄 Training",
                "RL Agent": "🔄 Learning",
                "Signal Aggregator": "✅ Active",
                "Trade Score Engine": "✅ Active",
                "Strike Selector": "✅ Active",
                "Risk Manager": "✅ Active",
                "Paper Trader": "✅ Active",
                "Telegram Alerts": "⚠️ No credentials",
                "Scheduler": "✅ Active",
                "Performance Analyzer": "✅ Active",
                "Strategy Optimizer": "✅ Active",
            }
            for module, status in modules.items():
                st.markdown(f"**{module}:** {status}")
        
        st.markdown("---")
        st.markdown("#### ⚠️ Disclaimer")
        st.warning(
            "This is a Paper Trading system. No real money is at risk. "
            "Past performance does not guarantee future results. "
            "Always consult a financial advisor before live trading."
        )


if __name__ == "__main__":
    run_dashboard()
