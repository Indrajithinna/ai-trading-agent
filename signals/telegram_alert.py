"""
Telegram Signal Generator (Module 13)
=======================================
Sends trade alerts via Telegram Bot API.
Formats signals in a professional, easy-to-read format.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

import requests

from ai_trading_agent.config import TelegramConfig
from ai_trading_agent.utils.helpers import get_ist_now, format_currency
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("TelegramAlert")


class TelegramAlertSystem:
    """
    Sends formatted trade signals and system alerts via Telegram Bot API.
    
    Message Types:
    - Trade Signals (BUY CALL / BUY PUT)
    - Trade Updates (Target Hit / SL Hit)
    - Daily Summary Reports
    - System Status Alerts
    """
    
    def __init__(self, config: TelegramConfig):
        self.config = config
        self._base_url = f"https://api.telegram.org/bot{config.bot_token}"
        self._message_count = 0
        self._enabled = bool(config.bot_token and config.chat_id)
        
        if self._enabled:
            logger.info("✅ TelegramAlertSystem initialized (enabled)")
        else:
            logger.warning("⚠️ TelegramAlertSystem initialized (disabled - no credentials)")
    
    def send_trade_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Send a trade signal alert.
        
        Expected signal format:
        {
            "symbol": "BANKNIFTY",
            "strike": 48500,
            "option_type": "CE",
            "direction": "BUY_CALL",
            "entry_price": 120,
            "target1": 150,
            "target2": 180,
            "stop_loss": 90,
            "trade_score": 83,
            "confirming_agents": 3,
            "total_agents": 4,
            "market_regime": "TRENDING",
            "ai_confidence": 78.5
        }
        """
        direction_emoji = "🟢" if signal.get("direction") == "BUY_CALL" else "🔴"
        direction_text = "BUY CALL" if signal.get("direction") == "BUY_CALL" else "BUY PUT"
        
        message = f"""
{direction_emoji} <b>═══ TRADE SIGNAL ═══</b> {direction_emoji}

📊 <b>{signal.get('symbol', 'N/A')} {signal.get('strike', 'N/A')} {signal.get('option_type', 'N/A')}</b>

📌 <b>{direction_text}</b>

💰 BUY ABOVE: <b>{signal.get('entry_price', 'N/A')}</b>
🎯 TARGET 1: <b>{signal.get('target1', 'N/A')}</b>
🎯 TARGET 2: <b>{signal.get('target2', 'N/A')}</b>
🛑 STOP LOSS: <b>{signal.get('stop_loss', 'N/A')}</b>

📈 TRADE SCORE: <b>{signal.get('trade_score', 'N/A')}%</b>
🤖 AGENTS CONFIRMING: <b>{signal.get('confirming_agents', 'N/A')}/{signal.get('total_agents', 'N/A')}</b>
🧠 AI CONFIDENCE: <b>{signal.get('ai_confidence', 'N/A')}%</b>
📊 REGIME: <b>{signal.get('market_regime', 'N/A')}</b>

⏰ {get_ist_now().strftime("%d-%b-%Y %I:%M:%S %p")} IST
━━━━━━━━━━━━━━━━━━━━
"""
        return self._send_message(message.strip())
    
    def send_trade_update(self, update: Dict[str, Any]) -> bool:
        """Send a trade update (target hit, SL hit, exit)."""
        status = update.get('status', 'UPDATE')
        pnl = update.get('pnl', 0)
        
        emoji = "🎯" if status == "TARGET_HIT" else "🛑" if status == "SL_HIT" else "📊"
        pnl_emoji = "💚" if pnl > 0 else "❤️"
        
        message = f"""
{emoji} <b>═══ TRADE UPDATE ═══</b> {emoji}

📊 <b>{update.get('symbol', 'N/A')} {update.get('strike', 'N/A')} {update.get('option_type', 'N/A')}</b>

📌 Status: <b>{status}</b>
💰 Entry: {update.get('entry_price', 'N/A')}
📍 Exit: {update.get('exit_price', 'N/A')}
{pnl_emoji} P&L: <b>{format_currency(pnl)}</b>

📈 Win Rate: {update.get('win_rate', 'N/A')}%
💰 Day P&L: {format_currency(update.get('daily_pnl', 0))}

⏰ {get_ist_now().strftime("%I:%M:%S %p")} IST
━━━━━━━━━━━━━━━━━━━━
"""
        return self._send_message(message.strip())
    
    def send_daily_summary(self, summary: Dict[str, Any]) -> bool:
        """Send end-of-day trading summary."""
        win_rate = summary.get('win_rate', 0)
        daily_pnl = summary.get('daily_pnl', 0)
        pnl_emoji = "💚" if daily_pnl > 0 else "❤️" if daily_pnl < 0 else "⚪"
        
        message = f"""
📋 <b>═══ DAILY TRADING SUMMARY ═══</b> 📋

📅 Date: <b>{get_ist_now().strftime("%d-%b-%Y")}</b>

{pnl_emoji} Daily P&L: <b>{format_currency(daily_pnl)}</b>

📊 <b>Trade Statistics:</b>
├ Total Trades: {summary.get('total_trades', 0)}
├ Winning: {summary.get('winning_trades', 0)} ✅
├ Losing: {summary.get('losing_trades', 0)} ❌
├ Win Rate: {win_rate:.1f}%
└ Max Drawdown: {format_currency(summary.get('max_drawdown', 0))}

💰 <b>Capital Status:</b>
├ Starting: {format_currency(summary.get('starting_capital', 0))}
├ Current: {format_currency(summary.get('current_capital', 0))}
└ Change: {format_currency(daily_pnl)} ({summary.get('daily_pnl_pct', 0):.2f}%)

🤖 <b>System Status:</b>
├ Signals Generated: {summary.get('signals_generated', 0)}
├ Signals Executed: {summary.get('signals_executed', 0)}
└ AI Accuracy: {summary.get('ai_accuracy', 'N/A')}%

⏰ Report generated at {get_ist_now().strftime("%I:%M:%S %p")} IST
━━━━━━━━━━━━━━━━━━━━
"""
        return self._send_message(message.strip())
    
    def send_system_alert(self, alert_type: str, message_text: str) -> bool:
        """Send a system status alert."""
        emoji_map = {
            "start": "🚀",
            "stop": "⏹️",
            "error": "🚨",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        emoji = emoji_map.get(alert_type, "📢")
        
        message = f"""
{emoji} <b>SYSTEM ALERT</b>

{message_text}

⏰ {get_ist_now().strftime("%d-%b-%Y %I:%M:%S %p")} IST
"""
        return self._send_message(message.strip())
    
    def _send_message(self, text: str) -> bool:
        """Send a message via Telegram Bot API."""
        if not self._enabled:
            logger.info(f"📱 [Telegram Disabled] Message would be sent:\n{text[:100]}...")
            self._message_count += 1
            return True
        
        try:
            url = f"{self._base_url}/sendMessage"
            payload = {
                "chat_id": self.config.chat_id,
                "text": text,
                "parse_mode": self.config.parse_mode,
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self._message_count += 1
                logger.info(f"📱 Telegram message sent (#{self._message_count})")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get messaging statistics."""
        return {
            "enabled": self._enabled,
            "messages_sent": self._message_count,
            "bot_configured": bool(self.config.bot_token),
            "chat_configured": bool(self.config.chat_id)
        }
