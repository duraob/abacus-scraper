"""
Telegram Bot for NFL AI Projection & Decision Engine
Sends alerts and notifications for betting recommendations and system updates
"""

import os
import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramBot:
    """Telegram bot for sending alerts and notifications"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not found in environment variables")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Telegram bot initialized successfully")
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send a message to the configured chat"""
        if not self.enabled:
            logger.warning("Telegram bot not enabled - skipping message")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            logger.info("Telegram message sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def send_betting_alert(self, bet: Dict) -> bool:
        """Send a formatted betting alert"""
        if not self.enabled:
            return False
        
        message = self._format_betting_alert(bet)
        return self.send_message(message)
    
    def send_weekly_summary(self, summary: Dict) -> bool:
        """Send a weekly summary of recommendations and performance"""
        if not self.enabled:
            return False
        
        message = self._format_weekly_summary(summary)
        return self.send_message(message)
    
    def send_system_alert(self, alert_type: str, message: str) -> bool:
        """Send a system alert (error, warning, info)"""
        if not self.enabled:
            return False
        
        formatted_message = self._format_system_alert(alert_type, message)
        return self.send_message(formatted_message)
    
    def send_batch_alerts(self, bets: List[Dict]) -> Dict[str, int]:
        """Send multiple betting alerts and return success/failure counts"""
        if not self.enabled:
            return {"sent": 0, "failed": 0}
        
        sent = 0
        failed = 0
        
        for bet in bets:
            if self.send_betting_alert(bet):
                sent += 1
            else:
                failed += 1
        
        logger.info(f"Batch alert results: {sent} sent, {failed} failed")
        return {"sent": sent, "failed": failed}
    
    def _format_betting_alert(self, bet: Dict) -> str:
        """Format a betting alert message"""
        confidence_emoji = "🟢" if bet.get('confidence', 0) >= 75 else "🟡"
        
        message = f"""
{confidence_emoji} <b>BETTING ALERT</b>

<b>Player:</b> {bet.get('player_name', 'Unknown')}
<b>Team:</b> {bet.get('team', 'Unknown')}
<b>Prop:</b> {bet.get('prop_type', 'Unknown')}
<b>Line:</b> {bet.get('line', 'Unknown')}
<b>Side:</b> <b>{bet.get('side', 'Unknown').upper()}</b>
<b>Confidence:</b> {bet.get('confidence', 0)}%

<b>Rationale:</b>
{bet.get('rationale', 'No rationale provided')}

<b>Projected Points:</b> {bet.get('projected_points', 0):.1f}
<b>Edge:</b> {bet.get('edge', 0):.1f}%
        """.strip()
        
        return message
    
    def _format_weekly_summary(self, summary: Dict) -> str:
        """Format a weekly summary message"""
        message = f"""
📊 <b>WEEKLY SUMMARY</b>

<b>Week:</b> {summary.get('week', 'Unknown')}
<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}

<b>Recommendations:</b>
• Total Picks: {summary.get('total_picks', 0)}
• High Confidence (75%+): {summary.get('high_confidence', 0)}
• Medium Confidence (60-74%): {summary.get('medium_confidence', 0)}

<b>Performance:</b>
• Win Rate: {summary.get('win_rate', 0):.1f}%
• Total P&L: ${summary.get('total_pnl', 0):.2f}
• Best Pick: {summary.get('best_pick', 'None')}

<b>Top Insights:</b>
{summary.get('top_insights', 'No insights available')}
        """.strip()
        
        return message
    
    def _format_system_alert(self, alert_type: str, message: str) -> str:
        """Format a system alert message"""
        emoji_map = {
            'error': '🔴',
            'warning': '🟡', 
            'info': '🔵',
            'success': '🟢'
        }
        
        emoji = emoji_map.get(alert_type.lower(), 'ℹ️')
        
        formatted_message = f"""
{emoji} <b>SYSTEM ALERT</b>

<b>Type:</b> {alert_type.upper()}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Message:</b>
{message}
        """.strip()
        
        return formatted_message
    
    def test_connection(self) -> bool:
        """Test the Telegram bot connection"""
        if not self.enabled:
            logger.warning("Telegram bot not enabled - cannot test connection")
            return False
        
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            bot_info = response.json()
            if bot_info.get('ok'):
                logger.info(f"Telegram bot connection successful: {bot_info['result']['username']}")
                return True
            else:
                logger.error("Telegram bot connection failed")
                return False
                
        except Exception as e:
            logger.error(f"Telegram bot connection test failed: {e}")
            return False
