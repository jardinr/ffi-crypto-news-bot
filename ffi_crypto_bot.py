#!/usr/bin/env python3
"""
FFI Crypto News Bot - Module 8 Enhanced Edition with Notion Portfolio Integration
Main orchestrator with integrated portfolio tracking
"""

import asyncio
import sys
import os
import csv
import re
from datetime import datetime
from typing import Dict, List, Optional

# Import configuration
from config import Config

# Import utilities
from utils.openai_client import OpenAIClient
from utils.discord_poster import DiscordPoster
from utils.telegram_poster import TelegramPoster

# Import modules
from modules.news_analyzer import NewsAnalyzer
from modules.news_summarizer import NewsSummarizer
from modules.etf_tracker import ETFTracker


class PortfolioTracker:
    """Simplified portfolio tracker with Notion integration."""
    
    def __init__(self, config):
        """Initialize portfolio tracker."""
        self.config = config
        self.portfolio_path = 'notion_portfolio.csv'  # In root directory
        
    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse price string to float."""
        if not price_str or price_str.strip() == '' or price_str == '-':
            return None
        
        cleaned = price_str.replace('$', '').replace(' ', '').replace(',', '.')
        match = re.search(r'[\d.]+', cleaned)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None
    
    def _parse_exit_targets(self, exit_str: str) -> List[Dict[str, float]]:
        """Parse exit target string."""
        if not exit_str or exit_str.strip() == '' or exit_str == '-':
            return []
        
        targets = []
        pattern = r'(\d+)\.\)\s*([\d.]+)\$\s*-\s*([\d.]+)\$'
        matches = re.findall(pattern, exit_str)
        
        for match in matches:
            level, low, high = match
            targets.append({
                'level': int(level),
                'low': float(low.replace(',', '.')),
                'high': float(high.replace(',', '.'))
            })
        
        return targets
    
    def _determine_tier(self, project_name: str, prev_tier: str) -> str:
        """Determine tier from project name."""
        if project_name.startswith('🏠'):
            return 'main'
        elif project_name.startswith('🎰'):
            return 'high_risk'
        elif project_name.startswith('⚖️'):
            return 'mid'
        elif project_name.startswith('🪨'):
            return 'safety'
        elif project_name == 'Nicht mehr priorisiert':
            return 'not_prioritized'
        else:
            return prev_tier
    
    def load_portfolio(self) -> Dict[str, List[Dict]]:
        """Load portfolio from CSV."""
        tiers = {
            'main': {'emoji': '🏠', 'name': 'Main Tier', 'coins': []},
            'high_risk': {'emoji': '🎰', 'name': 'High Risk Tier', 'coins': []},
            'mid': {'emoji': '⚖️', 'name': 'Mid Tier', 'coins': []},
            'safety': {'emoji': '🪨', 'name': 'Sicherheitspolster', 'coins': []},
        }
        
        try:
            with open(self.portfolio_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            current_tier = 'main'
            
            for row in rows:
                project = row.get('Project', '').strip()
                ticker = row.get('Ticker', '').strip()
                
                if project and not ticker:
                    current_tier = self._determine_tier(project, current_tier)
                    continue
                
                if not ticker or current_tier == 'not_prioritized':
                    continue
                
                coin = {
                    'name': project,
                    'ticker': ticker,
                    'buy_target': self._parse_price(row.get('Buy target', '')),
                    'conservative_exits': self._parse_exit_targets(row.get('Conservative exits', '')),
                    'optimistic_exits': self._parse_exit_targets(row.get('Optimistic exits', '')),
                }
                
                tiers[current_tier]['coins'].append(coin)
            
            return tiers
            
        except Exception as e:
            print(f"Error loading portfolio: {e}")
            return tiers
    
    async def fetch_prices(self, coins: List[Dict]) -> Dict[str, float]:
        """Fetch current prices from CoinGecko."""
        import aiohttp
        
        # Map tickers to CoinGecko IDs
        ticker_to_id = {
            'BTC': 'bitcoin', 'ETH': 'ethereum', 'DOT': 'polkadot', 'RIO': 'realio-network',
            'INJ': 'injective-protocol', 'TAO': 'bittensor', 'VRA': 'verasity',
            'NMT': 'netmind-token', 'RNDR': 'render-token', 'IOTX': 'iotex',
            'LINK': 'chainlink', 'HBAR': 'hedera-hashgraph', 'LL': 'lightlink',
            'QUBIC': 'qubic-network', 'XNA': 'neurai', 'ONDO': 'ondo-finance',
            'VET': 'vechain', 'DAG': 'constellation-labs'
        }
        
        prices = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                for coin in coins:
                    ticker = coin['ticker']
                    coin_id = ticker_to_id.get(ticker)
                    
                    if not coin_id:
                        continue
                    
                    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
                    
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if coin_id in data and 'usd' in data[coin_id]:
                                prices[ticker] = data[coin_id]['usd']
                    
                    await asyncio.sleep(0.5)  # Rate limiting
        
        except Exception as e:
            print(f"Error fetching prices: {e}")
        
        return prices
    
    def analyze_signals(self, coin: Dict, price: float) -> List[str]:
        """Analyze buy/sell signals for a coin."""
        signals = []
        
        # Buy signal
        if coin['buy_target'] and price <= coin['buy_target']:
            diff_pct = ((coin['buy_target'] - price) / coin['buy_target']) * 100
            signals.append(f"🟢 Kaufgelegenheit! Preis {diff_pct:.1f}% unter Kaufziel")
        
        # Conservative exits
        for target in coin['conservative_exits']:
            if target['low'] <= price <= target['high']:
                signals.append(f"📍 Konservatives Ziel {target['level']} erreicht")
            elif price > target['high']:
                signals.append(f"⚠️ Konservatives Ziel {target['level']} überschritten")
        
        # Optimistic exits
        for target in coin['optimistic_exits']:
            if target['low'] <= price <= target['high']:
                signals.append(f"🎯 Optimistisches Ziel {target['level']} erreicht")
            elif price > target['high']:
                signals.append(f"🚨 Optimistisches Ziel {target['level']} überschritten! 🚀")
        
        return signals
    
    async def run(self):
        """Run portfolio tracking."""
        print("\n" + "="*80)
        print("PORTFOLIO TRACKING")
        print("="*80)
        
        # Load portfolio
        tiers = self.load_portfolio()
        
        # Collect all coins
        all_coins = []
        for tier_data in tiers.values():
            all_coins.extend(tier_data['coins'])
        
        print(f"Loaded {len(all_coins)} coins from portfolio")
        
        # Fetch prices
        prices = await self.fetch_prices(all_coins)
        print(f"Fetched prices for {len(prices)} coins")
        
        # Analyze and prepare Discord message
        portfolio_data = {
            'total_coins': len(all_coins),
            'prices_fetched': len(prices),
            'tiers': {},
            'critical_signals': []
        }
        
        for tier_key, tier_data in tiers.items():
            if not tier_data['coins']:
                continue
            
            tier_info = {
                'name': tier_data['name'],
                'emoji': tier_data['emoji'],
                'coins': []
            }
            
            for coin in tier_data['coins']:
                ticker = coin['ticker']
                price = prices.get(ticker)
                
                if price:
                    signals = self.analyze_signals(coin, price)
                    
                    coin_info = {
                        'name': coin['name'],
                        'ticker': ticker,
                        'price': price,
                        'signals': signals
                    }
                    
                    tier_info['coins'].append(coin_info)
                    
                    # Collect critical signals
                    for signal in signals:
                        if '🚨' in signal or '🟢' in signal:
                            portfolio_data['critical_signals'].append({
                                'coin': f"{coin['name']} ({ticker})",
                                'signal': signal
                            })
            
            if tier_info['coins']:
                portfolio_data['tiers'][tier_key] = tier_info
        
        # Post to Discord
        await self.post_portfolio_update(portfolio_data)
        
        print("Portfolio tracking completed")
    
    async def post_portfolio_update(self, data: Dict):
        """Post portfolio update to Discord."""
        discord_poster = DiscordPoster(self.config)
        
        # Create main portfolio embed
        embed = {
            "title": "📈 Portfolio-Update",
            "description": f"**📊 Portfolio-Übersicht**\n"
                          f"Coins überwacht: {data['total_coins']}\n"
                          f"Preise abgerufen: {data['prices_fetched']}\n"
                          f"🟢 Kaufgelegenheiten: {sum(1 for s in data['critical_signals'] if '🟢' in s['signal'])}\n"
                          f"🔴 Verkaufssignale: {sum(1 for s in data['critical_signals'] if '🚨' in s['signal'])}",
            "color": 3447003,  # Blue
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "FFI Crypto Bot - Portfolio Tracker"}
        }
        
        # Add tier sections
        for tier_key, tier_info in data['tiers'].items():
            field_value = ""
            
            for coin in tier_info['coins'][:5]:  # Limit to 5 coins per tier
                field_value += f"\n**{coin['name']} ({coin['ticker']})**\n"
                field_value += f"Preis: ${coin['price']:,.2f}\n"
                
                if coin['signals']:
                    for signal in coin['signals'][:2]:  # Limit signals
                        field_value += f"{signal}\n"
                
                field_value += "\n"
            
            if field_value:
                embed["fields"] = embed.get("fields", [])
                embed["fields"].append({
                    "name": f"{tier_info['emoji']} {tier_info['name']}",
                    "value": field_value[:1024],  # Discord limit
                    "inline": False
                })
        
        # Post to Discord
        await discord_poster.post_embed(embed)
        
        # Post critical signals separately if any
        if data['critical_signals']:
            critical_embed = {
                "title": "🚨 Wichtige Portfolio-Signale",
                "description": "\n".join([f"• **{s['coin']}**: {s['signal']}" for s in data['critical_signals'][:10]]),
                "color": 15158332,  # Red
                "timestamp": datetime.utcnow().isoformat()
            }
            await discord_poster.post_embed(critical_embed)


async def main():
    """Main entry point."""
    print("🚀 Starting FFI Crypto News Bot...")
    
    # Load configuration
    config = Config()
    
    # Initialize components
    news_analyzer = NewsAnalyzer(config)
    news_summarizer = NewsSummarizer(config)
    etf_tracker = ETFTracker(config)
    portfolio_tracker = PortfolioTracker(config)
    
    # Run news analysis (existing functionality)
    await news_analyzer.run()
    
    # Run portfolio tracking (new functionality)
    try:
        await portfolio_tracker.run()
    except Exception as e:
        print(f"Portfolio tracking error: {e}")
        print("Continuing with other modules...")
    
    # Run news summarization
    try:
        await news_summarizer.run()
    except Exception as e:
        print(f"News summarization error: {e}")
    
    # Run ETF tracking
    try:
        await etf_tracker.run()
    except Exception as e:
        print(f"ETF tracking error: {e}")
    
    print("\n" + "="*80)
    print("FFI CRYPTO NEWS BOT COMPLETED SUCCESSFULLY")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
