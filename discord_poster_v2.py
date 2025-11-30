"""
Enhanced Discord Poster with Tier-Based Portfolio Support
"""

import aiohttp
from typing import Dict, List, Optional
from datetime import datetime

class DiscordPosterV2:
    """Enhanced Discord poster with tier-based portfolio formatting."""
    
    def __init__(self, webhooks: Dict[str, str]):
        """Initialize with Discord webhook URLs."""
        self.webhooks = webhooks
    
    async def post_message(self, content: str, title: Optional[str] = None, webhook_key: str = 'default'):
        """Post a simple message to Discord."""
        webhook_url = self.webhooks.get(webhook_key) or self.webhooks.get('default')
        if not webhook_url:
            return
        
        embed = {
            "description": content,
            "color": 3447003,  # Blue
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if title:
            embed["title"] = title
        
        payload = {"embeds": [embed]}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status != 204:
                        print(f"Discord webhook error: {response.status}")
        except Exception as e:
            print(f"Error posting to Discord: {e}")
    
    async def post_portfolio_update(self, portfolio_data: Dict):
        """Post tier-based portfolio update to Discord."""
        webhook_url = self.webhooks.get('default')
        if not webhook_url:
            return
        
        # Create embeds for each tier with signals
        embeds = []
        
        # Summary embed
        summary = portfolio_data['summary']
        summary_text = f"""
📊 **Portfolio-Übersicht**

Coins überwacht: {summary['total_coins']}
Preise abgerufen: {summary['prices_fetched']}
🟢 Kaufgelegenheiten: {summary['buy_opportunities']}
🔴 Verkaufssignale: {summary['exit_signals']}
"""
        
        embeds.append({
            "title": "📈 Portfolio-Update",
            "description": summary_text,
            "color": 3447003,  # Blue
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Tier embeds (only if there are signals)
        tier_colors = {
            'main': 5763719,  # Green
            'high_risk': 15158332,  # Red
            'mid': 16776960,  # Yellow
            'safety': 9807270  # Gray
        }
        
        for tier_key, tier_data in portfolio_data['tiers'].items():
            if not tier_data['coins']:
                continue
            
            # Collect coins with signals
            coins_with_signals = [c for c in tier_data['coins'] if c['signals']]
            
            if not coins_with_signals:
                continue
            
            tier_text = f"{tier_data['emoji']} **{tier_data['name']}**\n\n"
            
            for coin in coins_with_signals[:5]:  # Limit to 5 per tier
                tier_text += f"**{coin['name']} ({coin['symbol']})**\n"
                tier_text += f"Preis: ${coin['current_price']:.6f}\n"
                
                for signal in coin['signals']:
                    urgency_emoji = {
                        'critical': '🚨',
                        'high': '⚠️',
                        'medium': '📍',
                        'low': 'ℹ️'
                    }.get(signal['urgency'], '•')
                    
                    tier_text += f"{urgency_emoji} {signal['message']}\n"
                
                tier_text += "\n"
            
            if len(coins_with_signals) > 5:
                tier_text += f"_...und {len(coins_with_signals) - 5} weitere_\n"
            
            embeds.append({
                "description": tier_text,
                "color": tier_colors.get(tier_key, 3447003),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Post embeds (Discord limits to 10 embeds per message)
        if embeds:
            payload = {"embeds": embeds[:10]}
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(webhook_url, json=payload) as response:
                        if response.status != 204:
                            print(f"Discord webhook error: {response.status}")
            except Exception as e:
                print(f"Error posting portfolio to Discord: {e}")
    
    async def post_critical_signals(self, signals: List[Dict]):
        """Post only critical/high urgency signals."""
        webhook_url = self.webhooks.get('default')
        if not webhook_url:
            return
        
        critical_signals = [s for s in signals if s['urgency'] in ['critical', 'high']]
        
        if not critical_signals:
            return
        
        content = "🚨 **Wichtige Portfolio-Signale**\n\n"
        
        for signal in critical_signals[:10]:
            emoji = '🚨' if signal['urgency'] == 'critical' else '⚠️'
            content += f"{emoji} **{signal['coin']} ({signal['symbol']})**\n"
            content += f"   {signal['message']}\n"
            content += f"   _Tier: {signal['tier']}_\n\n"
        
        embed = {
            "description": content,
            "color": 15158332,  # Red
            "timestamp": datetime.utcnow().isoformat()
        }
        
        payload = {"embeds": [embed]}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status != 204:
                        print(f"Discord webhook error: {response.status}")
        except Exception as e:
            print(f"Error posting critical signals to Discord: {e}")

