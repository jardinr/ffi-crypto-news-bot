#!/usr/bin/env python3
"""
FFI Crypto News Bot - Module 8 Enhanced Edition
Advanced news analysis with significance scoring, credibility ratings, and smart article selection
"""

import asyncio
import aiohttp
import feedparser
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Simple print-based logging
def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - {message}")

class FFICryptoNewsBot:
    """Enhanced crypto news bot with Module 8 advanced news analysis."""
    
    def __init__(self):
        """Initialize the FFI Crypto News Bot with Module 8 features."""
        self.config = {
            'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
            'discord_webhook': os.getenv('DISCORD_WEBHOOK_URL', ''),
            'discord_webhook_ffi': os.getenv('DISCORD_WEBHOOK_FFI', ''),
            'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
            'max_articles': int(os.getenv('MAX_ARTICLES_PER_RUN', '8')),
            'hours_lookback': int(os.getenv('HOURS_LOOKBACK', '1')),
            'min_significance_score': float(os.getenv('MIN_SIGNIFICANCE_SCORE', '2.0'))
        }
        
        # Collect all Discord webhooks
        self.discord_webhooks = []
        if self.config['discord_webhook']:
            self.discord_webhooks.append(('Original Discord', self.config['discord_webhook']))
        if self.config['discord_webhook_ffi']:
            self.discord_webhooks.append(('FFI Discord', self.config['discord_webhook_ffi']))
        
        log(f"Configured {len(self.discord_webhooks)} Discord webhook(s)")
        
        # RSS feeds with credibility scores (Module 8 feature)
        self.rss_feeds = {
            'CoinDesk': {
                'url': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
                'credibility': 4  # 1-5 scale
            },
            'The Block': {
                'url': 'https://www.theblock.co/rss.xml',
                'credibility': 4
            },
            'Decrypt': {
                'url': 'https://decrypt.co/feed',
                'credibility': 4
            },
            'Cointelegraph': {
                'url': 'https://cointelegraph.com/rss',
                'credibility': 3
            },
            'CryptoSlate': {
                'url': 'https://cryptoslate.com/feed/',
                'credibility': 3
            },
            'Bitcoinist': {
                'url': 'https://bitcoinist.com/feed/',
                'credibility': 3
            }
        }
        
        # Crypto keywords
        self.crypto_keywords = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency', 
            'blockchain', 'defi', 'nft', 'altcoin', 'solana', 'cardano', 
            'polkadot', 'chainlink', 'dogecoin', 'shiba', 'matic', 'polygon',
            'binance', 'coinbase', 'trading', 'hodl', 'mining', 'staking',
            'web3', 'metaverse', 'dao', 'yield', 'liquidity', 'dex', 'cefi'
        ]
        
        # Load processed articles
        self.processed_file = 'processed_articles.json'
        self.processed_articles = self.load_processed_articles()
        
        log(f"Loaded {len(self.processed_articles)} processed articles")
    
    async def load_portfolio_from_csv(self) -> Dict:
        """Load portfolio from notion_portfolio.csv with correct Sicherheitspolster handling"""
        import csv
        
        tiers = {
            'main': {'emoji': '🏠', 'name': 'Main Tier', 'coins': []},
            'high_risk': {'emoji': '🎰', 'name': 'High Risk Tier', 'coins': []},
            'mid': {'emoji': '⚖️', 'name': 'Mid Tier', 'coins': []},
            'safety': {'emoji': '🪨', 'name': 'Sicherheitspolster', 'coins': []},
        }
        
        try:
            with open('notion_portfolio.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            current_tier = 'main'
            skip_mode = False  # Skip coins after "Nicht mehr priorisiert" until Sicherheitspolster
            
            for row in rows:
                project = row.get('Project', '').strip()
                ticker = row.get('Ticker', '').strip()
                
                # Check for "Nicht mehr priorisiert" - start skipping
                if 'nicht mehr priorisiert' in project.lower():
                    skip_mode = True
                    continue
                
                # Check for Sicherheitspolster - stop skipping
                if project.startswith('🪨'):
                    current_tier = 'safety'
                    skip_mode = False
                    continue
                
                # Detect other tier headers
                if project.startswith('🏠'):
                    current_tier = 'main'
                    continue
                elif project.startswith('🎰'):
                    current_tier = 'high_risk'
                    continue
                elif project.startswith('⚖️'):
                    current_tier = 'mid'
                    continue
                
                # Skip if in skip mode
                if skip_mode:
                    continue
                
                # Skip empty rows
                if not ticker or not project:
                    continue
                
                # Parse targets
                conservative = row.get('Conservative exits', '').strip()
                optimistic = row.get('Optimistic exits', '').strip()
                
                coin_data = {
                    'name': project,
                    'symbol': ticker.upper(),
                    'conservative_targets': self._parse_targets(conservative),
                    'optimistic_targets': self._parse_targets(optimistic),
                }
                
                tiers[current_tier]['coins'].append(coin_data)
            
            total_coins = sum(len(t['coins']) for t in tiers.values())
            log(f"Loaded portfolio: {total_coins} coins across 4 tiers")
            return tiers
            
        except Exception as e:
            log(f"Error loading portfolio: {e}")
            return tiers
    
    def _parse_targets(self, target_str: str) -> List[Dict]:
        """Parse target string like '1.) 11.888$-14.273$ 2.) 21.188$-24.359$'"""
        import re
        
        if not target_str or target_str == '-':
            return []
        
        targets = []
        pattern = r'(\d+)\.\)\s*([\d.]+)\$\s*-\s*([\d.]+)\$'
        matches = re.findall(pattern, target_str)
        
        for match in matches:
            level, low, high = match
            targets.append({
                'level': int(level),
                'low': float(low.replace(',', '.')),
                'high': float(high.replace(',', '.'))
            })
        
        return targets
    
    async def fetch_coin_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Fetch current prices from CoinGecko"""
        symbol_to_id = {
            'BTC': 'bitcoin', 'ETH': 'ethereum', 'DOT': 'polkadot',
            'RIO': 'realio-network', 'INJ': 'injective-protocol',
            'TAO': 'bittensor', 'VRA': 'verasity', 'NMT': 'netmind-token',
            'RENDER': 'render-token', 'IOTX': 'iotex', 'LINK': 'chainlink',
            'HBAR': 'hedera-hashgraph', 'LL': 'lightlink', 'QUBIC': 'qubic-network',
            'ZEPH': 'zephyr-protocol', 'BCH': 'bitcoin-cash', 'KNDX': 'kondux',
            'VELO': 'velo', 'ALPH': 'alephium', 'KAS': 'kaspa',
            'HYPE': 'hyperliquid', 'OCTA': 'octaspace', 'XNA': 'neurai',
            'ONDO': 'ondo-finance', 'VET': 'vechain', 'DAG': 'constellation-labs'
        }
        
        prices = {}
        
        try:
            ids = [symbol_to_id.get(sym, sym.lower()) for sym in symbols if sym in symbol_to_id]
            
            if not ids:
                return prices
            
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies=usd"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for symbol in symbols:
                            coin_id = symbol_to_id.get(symbol, symbol.lower())
                            if coin_id in data and 'usd' in data[coin_id]:
                                prices[symbol] = data[coin_id]['usd']
            
            log(f"Fetched prices for {len(prices)}/{len(symbols)} coins")
            
        except Exception as e:
            log(f"Error fetching prices: {e}")
        
        return prices
    
    def analyze_portfolio_signals(self, tiers: Dict, prices: Dict[str, float]) -> Dict:
        """Analyze portfolio for buy/sell signals"""
        signals = {
            'buy_opportunities': [],
            'sell_signals': [],
            'critical_alerts': []
        }
        
        for tier_key, tier_data in tiers.items():
            for coin in tier_data['coins']:
                symbol = coin['symbol']
                price = prices.get(symbol)
                
                if not price:
                    continue
                
                # Check conservative targets
                for target in coin['conservative_targets']:
                    if price >= target['low'] and price <= target['high']:
                        signals['sell_signals'].append({
                            'coin': coin['name'],
                            'symbol': symbol,
                            'price': price,
                            'target_level': target['level'],
                            'target_type': 'conservative',
                            'tier': tier_key
                        })
                    elif price > target['high']:
                        signals['critical_alerts'].append({
                            'coin': coin['name'],
                            'symbol': symbol,
                            'price': price,
                            'target_level': target['level'],
                            'target_type': 'conservative',
                            'message': f'Konservatives Ziel {target["level"]} überschritten!',
                            'tier': tier_key
                        })
                
                # Check optimistic targets
                for target in coin['optimistic_targets']:
                    if price >= target['low'] and price <= target['high']:
                        signals['sell_signals'].append({
                            'coin': coin['name'],
                            'symbol': symbol,
                            'price': price,
                            'target_level': target['level'],
                            'target_type': 'optimistic',
                            'tier': tier_key
                        })
                    elif price > target['high']:
                        signals['critical_alerts'].append({
                            'coin': coin['name'],
                            'symbol': symbol,
                            'price': price,
                            'target_level': target['level'],
                            'target_type': 'optimistic',
                            'message': f'Optimistisches Ziel {target["level"]} überschritten! 🚀',
                            'tier': tier_key
                        })
        
        return signals
    
    async def send_portfolio_update(self, tiers: Dict, prices: Dict[str, float], signals: Dict):
        """Send portfolio update to Discord (German) and Telegram (English)"""
        
        # Build German message for Discord
        message_de = "📈 **Portfolio-Update**\n\n"
        message_de += f"📊 **Portfolio-Übersicht**\n"
        message_de += f"Coins überwacht: {sum(len(t['coins']) for t in tiers.values())}\n"
        message_de += f"Preise abgerufen: {len(prices)}\n"
        message_de += f"🟢 Kaufgelegenheiten: {len([s for s in signals['buy_opportunities']])}\n"
        message_de += f"🔴 Verkaufssignale: {len(signals['sell_signals'])}\n\n"
        
        # Build English message for Telegram
        message_en = "📈 **Portfolio Update**\n\n"
        message_en += f"📊 **Portfolio Overview**\n"
        message_en += f"Coins monitored: {sum(len(t['coins']) for t in tiers.values())}\n"
        message_en += f"Prices fetched: {len(prices)}\n"
        message_en += f"🟢 Buy opportunities: {len([s for s in signals['buy_opportunities']])}\n"
        message_en += f"🔴 Sell signals: {len(signals['sell_signals'])}\n\n"
        
        # Tier name translations
        tier_names_en = {
            'main': 'Main Tier',
            'high_risk': 'High Risk Tier',
            'mid': 'Mid Tier',
            'safety': 'Safety Cushion'
        }
        
        # Add tier sections
        for tier_key in ['main', 'high_risk', 'mid', 'safety']:
            tier_data = tiers[tier_key]
            if not tier_data['coins']:
                continue
            
            # German version
            message_de += f"**{tier_data['emoji']} {tier_data['name']}**\n"
            
            # English version
            message_en += f"**{tier_data['emoji']} {tier_names_en[tier_key]}**\n"
            
            for coin in tier_data['coins'][:3]:  # Show first 3 per tier
                symbol = coin['symbol']
                price = prices.get(symbol)
                
                if price:
                    coin_line = f"• {coin['name']} ({symbol}) - ${price:,.2f}\n"
                    message_de += coin_line
                    message_en += coin_line
            
            if len(tier_data['coins']) > 3:
                message_de += f"  ... und {len(tier_data['coins']) - 3} weitere\n"
                message_en += f"  ... and {len(tier_data['coins']) - 3} more\n"
            
            message_de += "\n"
            message_en += "\n"
        
        # Add critical alerts
        if signals['critical_alerts']:
            message_de += "\n🚨 **Wichtige Portfolio-Signale**\n"
            message_en += "\n🚨 **Important Portfolio Signals**\n"
            for alert in signals['critical_alerts'][:5]:
                message_de += f"• {alert['coin']} ({alert['symbol']}): {alert['message']}\n"
                message_en += f"• {alert['coin']} ({alert['symbol']}): {alert['message']}\n"
        
        # Send German to Discord
        for webhook_name, webhook_url in self.discord_webhooks:
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {"content": message_de}
                    async with session.post(webhook_url, json=payload) as response:
                        if response.status == 204:
                            log(f"Portfolio update sent to {webhook_name} (German)")
                        else:
                            log(f"Failed to send portfolio update to {webhook_name}: {response.status}")
            except Exception as e:
                log(f"Error sending portfolio update to {webhook_name}: {e}")
        
        # Send English to Telegram
        try:
            await self.send_to_telegram(message_en)
            log("Portfolio update sent to Telegram (English)")
        except Exception as e:
            log(f"Error sending portfolio update to Telegram: {e}")
    
    def load_processed_articles(self) -> set:
        """Load previously processed article URLs and last run time."""
        try:
            if os.path.exists(self.processed_file):
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                    self.last_run_time = data.get('last_run_time', None)
                    if self.last_run_time:
                        log(f"Last successful run: {self.last_run_time}")
                    return set(data.get('articles', []))
        except Exception as e:
            log(f"Could not load processed articles: {e}")
        self.last_run_time = None
        return set()
    
    def save_processed_articles(self):
        """Save processed article URLs and current run time."""
        try:
            recent_articles = list(self.processed_articles)[-100:]
            data = {
                'articles': recent_articles,
                'last_updated': datetime.now().isoformat(),
                'last_run_time': datetime.now().isoformat()
            }
            with open(self.processed_file, 'w') as f:
                json.dump(data, f, indent=2)
            log(f"Saved {len(recent_articles)} processed articles")
        except Exception as e:
            log(f"Could not save processed articles: {e}")
    
    def is_crypto_related(self, title: str, description: str = '') -> bool:
        """Check if article is cryptocurrency-related."""
        text = f"{title} {description}".lower()
        return any(keyword in text for keyword in self.crypto_keywords)
    
    def is_recent(self, published_time: str, hours_back: int = None) -> Tuple[bool, str]:
        """Check if article was published recently. Returns (is_recent, age_description)."""
        try:
            if hours_back is None:
                hours_back = self.config['hours_lookback']
            
            # Try multiple date formats
            pub_time = None
            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z', 
                       '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%SZ']:
                try:
                    pub_time = datetime.strptime(published_time, fmt)
                    if pub_time.tzinfo is None:
                        pub_time = pub_time.replace(tzinfo=None)
                    else:
                        pub_time = pub_time.replace(tzinfo=None)  # Convert to naive for comparison
                    break
                except:
                    continue
            
            if pub_time is None:
                # Fallback to feedparser time parsing
                try:
                    pub_time = datetime.fromtimestamp(time.mktime(time.strptime(published_time)))
                except:
                    log(f"Could not parse timestamp: {published_time}")
                    return (False, "unknown age")  # Reject articles with unparseable dates
            
            now = datetime.now()
            age = now - pub_time
            cutoff_time = now - timedelta(hours=hours_back)
            
            # Calculate age description
            if age.total_seconds() < 3600:
                age_desc = f"{int(age.total_seconds() / 60)} minutes old"
            elif age.total_seconds() < 86400:
                age_desc = f"{int(age.total_seconds() / 3600)} hours old"
            else:
                age_desc = f"{int(age.total_seconds() / 86400)} days old"
            
            is_recent = pub_time > cutoff_time
            return (is_recent, age_desc)
        except Exception as e:
            log(f"Error checking article age: {e}")
            return (False, "error parsing date")
    
    def calculate_market_impact_score(self, title: str, description: str) -> int:
        """Calculate market impact score (1-5) - Module 8 feature."""
        text = f"{title} {description}".lower()
        
        # High impact keywords (score 5)
        high_impact = ['sec', 'regulation', 'ban', 'approval', 'etf', 'lawsuit', 
                       'hack', 'exploit', 'breach', 'shutdown', 'halving', 'merge']
        
        # Medium-high impact (score 4)
        medium_high = ['blackrock', 'fidelity', 'institutional', 'adoption', 
                       'partnership', 'integration', 'upgrade', 'fork']
        
        # Medium impact (score 3)
        medium = ['binance', 'coinbase', 'exchange', 'trading', 'volume', 
                  'price', 'market cap', 'whale']
        
        if any(keyword in text for keyword in high_impact):
            return 5
        elif any(keyword in text for keyword in medium_high):
            return 4
        elif any(keyword in text for keyword in medium):
            return 3
        else:
            return 2
    
    def calculate_relevance_score(self, title: str, description: str) -> int:
        """Calculate relevance score (1-5) based on coin importance - Module 8 feature."""
        text = f"{title} {description}".lower()
        
        # Tier 1: Bitcoin, Ethereum, Market-wide (score 5)
        if any(word in text for word in ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto market', 'cryptocurrency market']):
            return 5
        
        # Tier 2: Major altcoins (score 4)
        elif any(word in text for word in ['solana', 'cardano', 'polkadot', 'xrp', 'chainlink']):
            return 4
        
        # Tier 3: Popular altcoins (score 3)
        elif any(word in text for word in ['avalanche', 'polygon', 'matic', 'arbitrum', 'optimism']):
            return 3
        
        # Default: Other coins (score 2)
        else:
            return 2
    
    def analyze_sentiment_enhanced(self, title: str, description: str) -> Tuple[int, str, str]:
        """Enhanced sentiment analysis with numeric score - Module 8 feature."""
        text = f"{title} {description}".lower()
        
        positive_words = ['surge', 'rally', 'bull', 'gain', 'rise', 'up', 'high', 'moon', 
                         'breakthrough', 'adoption', 'partnership', 'launch', 'upgrade', 
                         'soar', 'jump', 'spike', 'boom', 'success']
        
        negative_words = ['crash', 'dump', 'bear', 'fall', 'drop', 'down', 'low', 'hack',
                         'ban', 'regulation', 'concern', 'warning', 'risk', 'decline',
                         'plunge', 'collapse', 'fail', 'scam', 'fraud']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        # Calculate sentiment score (-5 to +5)
        sentiment_score = positive_count - negative_count
        sentiment_score = max(-5, min(5, sentiment_score))  # Clamp to range
        
        if sentiment_score > 0:
            sentiment_label = 'Bullish'
            color = 'green'
        elif sentiment_score < 0:
            sentiment_label = 'Bearish'
            color = 'red'
        else:
            sentiment_label = 'Neutral'
            color = 'yellow'
        
        return sentiment_score, sentiment_label, color
    
    def calculate_time_impact_score(self, title: str, description: str) -> int:
        """Calculate time impact/urgency score (1-5) - Module 8 feature."""
        text = f"{title} {description}".lower()
        
        # Immediate urgency (score 5)
        if any(word in text for word in ['breaking', 'just in', 'alert', 'emergency', 'now']):
            return 5
        
        # Short-term (score 4)
        elif any(word in text for word in ['today', 'announced', 'hours ago', 'this morning']):
            return 4
        
        # Medium-term (score 3)
        elif any(word in text for word in ['this week', 'upcoming', 'soon', 'scheduled']):
            return 3
        
        # Default (score 2)
        else:
            return 2
    
    def calculate_significance_score(self, article: Dict, credibility: int) -> Dict:
        """Calculate total significance score - Module 8 feature."""
        title = article['title']
        description = article['description']
        
        # Individual scores
        market_impact = self.calculate_market_impact_score(title, description)
        relevance = self.calculate_relevance_score(title, description)
        sentiment_score, sentiment_label, sentiment_color = self.analyze_sentiment_enhanced(title, description)
        time_impact = self.calculate_time_impact_score(title, description)
        
        # Weighted total score (0-5 scale)
        total_score = (
            credibility * 0.20 +
            market_impact * 0.30 +
            relevance * 0.20 +
            abs(sentiment_score) * 0.15 +
            time_impact * 0.15
        )
        
        # Classification
        if total_score >= 3.5:
            classification = 'High Impact'
            classification_emoji = '🚨'
        elif total_score >= 2.5:
            classification = 'Medium Impact'
            classification_emoji = '📊'
        else:
            classification = 'Low Impact'
            classification_emoji = 'ℹ️'
        
        return {
            'credibility': credibility,
            'market_impact': market_impact,
            'relevance': relevance,
            'sentiment_score': sentiment_score,
            'sentiment_label': sentiment_label,
            'sentiment_color': sentiment_color,
            'time_impact': time_impact,
            'total_score': round(total_score, 1),
            'classification': classification,
            'classification_emoji': classification_emoji
        }
    
    async def fetch_rss_feed(self, session: aiohttp.ClientSession, name: str, feed_data: Dict) -> List[Dict]:
        """Fetch and parse RSS feed with credibility scoring."""
        try:
            url = feed_data['url']
            credibility = feed_data['credibility']
            
            log(f"Fetching RSS feed from {name} (credibility: {credibility}/5)")
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)
                    
                    articles = []
                    for entry in feed.entries:
                        # Check if crypto-related first
                        if not self.is_crypto_related(entry.title, getattr(entry, 'summary', '')):
                            continue
                        
                        # Check recency with age info
                        published = getattr(entry, 'published', '')
                        is_recent, age_desc = self.is_recent(published)
                        
                        # Skip if already processed
                        if entry.link in self.processed_articles:
                            continue
                        
                        # Skip if not recent
                        if not is_recent:
                            log(f"Skipping old article ({age_desc}): {entry.title[:50]}...")
                            continue
                        
                        # Check if article is ABOUT old events (even if recently published)
                        title_lower = entry.title.lower()
                        summary_lower = getattr(entry, 'summary', '').lower()
                        old_event_keywords = [
                            # Past time references
                            'yesterday', 'gestern', 'einen tag nach', 'one day after',
                            'last week', 'letzte woche', 'days ago', 'vor tagen',
                            'last month', 'letzten monat', 'weeks ago', 'vor wochen',
                            # Daily summaries and newsletters
                            'tagesnachrichten', 'daily news', 'the daily', 'newsletter',
                            'daily roundup', 'roundup', 'zusammenfassung', 'wochentagnachmittagen',
                            'weekly roundup', 'wochenrückblick', 'recap', 'rückblick'
                        ]
                        
                        is_about_old_event = any(keyword in title_lower or keyword in summary_lower 
                                                for keyword in old_event_keywords)
                        
                        if is_about_old_event:
                            log(f"Skipping article about past events: {entry.title[:50]}...")
                            continue
                        
                        log(f"Found fresh article ({age_desc}): {entry.title[:50]}...")
                        
                        article = {
                            'title': entry.title,
                            'link': entry.link,
                            'description': getattr(entry, 'summary', '')[:300],
                            'source': name,
                            'published': published,
                            'credibility': credibility,
                            'age': age_desc
                        }
                        
                        # Calculate significance scores
                        scores = self.calculate_significance_score(article, credibility)
                        article.update(scores)
                        
                        articles.append(article)
                    
                    log(f"Found {len(articles)} new crypto articles from {name}")
                    return articles
                else:
                    log(f"Failed to fetch {name}: HTTP {response.status}")
        except Exception as e:
            log(f"Error fetching {name}: {e}")
        return []
    
    async def translate_to_german(self, text: str) -> str:
        """Translate text to German using OpenAI."""
        try:
            if not self.config['openai_api_key']:
                return "[Translation unavailable]"
            
            url = "https://api.openai.com/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.config['openai_api_key']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional translator. Translate the following text to German. Keep technical terms and proper nouns in their original form when appropriate. Provide only the German translation."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        result = await response.json()
                        german_text = result['choices'][0]['message']['content'].strip()
                        log(f"Translated: {text[:30]}... -> {german_text[:30]}...")
                        return german_text
                    else:
                        error_text = await response.text()
                        log(f"OpenAI translation failed: HTTP {response.status}")
                        return "[Translation failed]"
        except Exception as e:
            log(f"Translation error: {e}")
            return "[Translation error]"
    
    def format_article_for_telegram(self, article: Dict, german_title: str = None, german_desc: str = None) -> str:
        """Format article for Telegram in ENGLISH with Module 8 significance indicators."""
        stars = '⭐' * article['credibility']
        
        # Keep classification in English for Telegram
        message = f"{article['classification_emoji']} **{article['classification'].upper()}**\n\n"
        
        # Use ENGLISH title and description for Telegram
        message += f"**{article['title']}**\n\n"
        
        message += f"📊 Significance: {article['total_score']}/5\n"
        message += f"⭐ Credibility: {stars} ({article['credibility']}/5)\n"
        message += f"📈 Market Impact: {article['market_impact']}/5\n"
        message += f"🎯 Relevance: {article['relevance']}/5\n"
        message += f"💭 Sentiment: {article['sentiment_label']} ({article['sentiment_score']:+d})\n"
        message += f"⏰ Time Urgency: {article['time_impact']}/5\n\n"
        
        message += f"{article['description']}\n\n"
        
        message += f"Source: {article['source']} | [Read more]({article['link']})"
        
        return message
    
    def format_article_for_discord(self, article: Dict, german_title: str = None, german_desc: str = None) -> Dict:
        """Format article for Discord webhook with Module 8 significance indicators."""
        color_map = {'green': 0x00ff00, 'red': 0xff0000, 'yellow': 0xffff00}
        embed_color = color_map.get(article['sentiment_color'], 0x0099ff)
        
        stars = '⭐' * article['credibility']
        
        # Use German title if available, otherwise English
        display_title = german_title if (german_title and "[" not in german_title) else article['title']
        title = f"{article['classification_emoji']} {display_title}"
        
        # Use German title if available, otherwise English
        display_title = german_title if (german_title and "[" not in german_title) else article['title']
        display_desc = german_desc if (german_desc and "[" not in german_desc) else article['description']
        
        # Translate classification and sentiment to German
        classification_de = {
            'High Impact': 'HOHE BEDEUTUNG',
            'Medium Impact': 'MITTLERE BEDEUTUNG',
            'Low Impact': 'GERINGE BEDEUTUNG'
        }.get(article['classification'], article['classification'].upper())
        
        sentiment_de = {
            'Bullish': 'Bullisch',
            'Bearish': 'Bärisch',
            'Neutral': 'Neutral'
        }.get(article['sentiment_label'], article['sentiment_label'])
        
        description = f"**📊 Bedeutung: {article['classification_emoji']} {classification_de} (Punktzahl: {article['total_score']}/5)**\n"
        description += f"**⭐ Quellenglaubwürdigkeit:** {stars} ({article['credibility']}/5)\n"
        description += f"**📈 Marktauswirkung:** {article['market_impact']}/5 | **🎯 Relevanz:** {article['relevance']}/5 | **⏰ Dringlichkeit:** {article['time_impact']}/5\n"
        description += f"**💭 Stimmung:** {sentiment_de} ({article['sentiment_score']:+d})\n\n"
        
        description += f"{display_desc}\n\n"
        
        description += f"**Klassifizierung:** {classification_de.title()}\n"
        description += f"**Quelle:** {article['source']}\n"
        description += f"**Stimmung:** {sentiment_de}"
        
        embed = {
            "embeds": [{
                "title": title[:256],  # Discord title limit
                "description": description[:4096],  # Discord description limit
                "url": article['link'],
                "color": embed_color,
                "footer": {
                    "text": f"FFI Crypto News Bot - Module 8 Enhanced • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                }
            }]
        }
        
        return embed
    
    async def send_to_telegram(self, message: str):
        """Send message to Telegram."""
        if not self.config['telegram_token'] or not self.config['telegram_chat_id']:
            log("Telegram not configured")
            return
        
        try:
            url = f"https://api.telegram.org/bot{self.config['telegram_token']}/sendMessage"
            payload = {
                'chat_id': self.config['telegram_chat_id'],
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        log("Sent to Telegram: " + message.split('\n')[0][:50] + "...")
                    else:
                        log(f"Telegram failed: HTTP {response.status}")
        except Exception as e:
            log(f"Telegram error: {e}")
    
    async def send_to_all_discord_webhooks(self, embed_data: Dict):
        """Send embed to all configured Discord webhooks."""
        if not self.discord_webhooks:
            log("No Discord webhooks configured")
            return
        
        title = embed_data['embeds'][0]['title'][:50]
        
        for webhook_name, webhook_url in self.discord_webhooks:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        webhook_url,
                        json=embed_data,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status in [200, 204]:
                            log(f"Sent to {webhook_name}: {title}...")
                        else:
                            log(f"{webhook_name} failed: HTTP {response.status}")
            except Exception as e:
                log(f"{webhook_name} error: {e}")
            
            await asyncio.sleep(0.3)
    
    async def process_articles(self, articles: List[Dict]):
        """Process articles with German translation and send to all platforms."""
        if not articles:
            log("No new articles to process")
            return
        
        log(f"Processing {len(articles)} articles with Module 8 significance scoring")
        log(f"Will deliver to: {len(self.discord_webhooks)} Discord server(s) + Telegram")
        
        for i, article in enumerate(articles, 1):
            try:
                log(f"\nArticle {i}/{len(articles)}: {article['title'][:60]}...")
                log(f"  Significance: {article['total_score']}/5 ({article['classification']})")
                log(f"  Credibility: {article['credibility']}/5, Market: {article['market_impact']}/5, Relevance: {article['relevance']}/5")
                
                # Translate to German
                german_title = await self.translate_to_german(article['title'])
                await asyncio.sleep(0.5)
                
                german_desc = await self.translate_to_german(article['description'])
                await asyncio.sleep(0.5)
                
                # Format for platforms
                telegram_message = self.format_article_for_telegram(article, german_title, german_desc)
                discord_embed = self.format_article_for_discord(article, german_title, german_desc)
                
                # Send to all Discord webhooks
                await self.send_to_all_discord_webhooks(discord_embed)
                await asyncio.sleep(0.5)
                
                # Send to Telegram
                await self.send_to_telegram(telegram_message)
                await asyncio.sleep(0.5)
                
                # Mark as processed
                self.processed_articles.add(article['link'])
                
            except Exception as e:
                log(f"Error processing article {article['title']}: {e}")
    
    async def run(self):
        """Main execution function."""
        log("=" * 80)
        log("FFI CRYPTO NEWS BOT - MODULE 8 ENHANCED EDITION")
        log("Advanced News Analysis + Dual-Language + Multi-Platform")
        log("=" * 80)
        log(f"Discord Servers: {len(self.discord_webhooks)}")
        log(f"Telegram: {'Enabled' if self.config['telegram_token'] else 'Disabled'}")
        log(f"Translation: {'Enabled (OpenAI)' if self.config['openai_api_key'] else 'Disabled'}")
        log(f"Min Significance Score: {self.config['min_significance_score']}")
        log("=" * 80)
        
        try:
            # Fetch articles from all RSS feeds
            async with aiohttp.ClientSession() as session:
                tasks = [self.fetch_rss_feed(session, name, feed_data) 
                        for name, feed_data in self.rss_feeds.items()]
                results = await asyncio.gather(*tasks)
            
            # Flatten articles
            all_articles = [article for sublist in results for article in sublist]
            
            # Filter by minimum significance score
            filtered_articles = [a for a in all_articles 
                               if a['total_score'] >= self.config['min_significance_score']]
            
            # Sort by significance score (highest first)
            filtered_articles.sort(key=lambda x: x['total_score'], reverse=True)
            
            # Limit to max articles
            articles_to_process = filtered_articles[:self.config['max_articles']]
            
            log(f"\nFound {len(all_articles)} total new articles")
            log(f"After filtering (score >= {self.config['min_significance_score']}): {len(filtered_articles)} articles")
            log(f"Processing top {len(articles_to_process)} by significance score")
            
            # Process and send articles
            await self.process_articles(articles_to_process)
            
            # Save processed articles
            self.save_processed_articles()
            
            log("\n" + "=" * 80)
            
            # Portfolio tracking
            log("\n" + "=" * 80)
            log("STARTING PORTFOLIO TRACKING")
            log("=" * 80)
            
            try:
                tiers = await self.load_portfolio_from_csv()
                all_symbols = []
                for tier_data in tiers.values():
                    all_symbols.extend([coin['symbol'] for coin in tier_data['coins']])
                
                prices = await self.fetch_coin_prices(all_symbols)
                signals = self.analyze_portfolio_signals(tiers, prices)
                await self.send_portfolio_update(tiers, prices, signals)
                
                log("Portfolio tracking completed successfully")
            except Exception as e:
                log(f"Portfolio tracking error: {e}")
            
            log("FFI CRYPTO NEWS BOT COMPLETED SUCCESSFULLY")
            log("=" * 80)
            
        except Exception as e:
            log(f"Critical error: {e}")
            raise

def main():
    """Entry point for the bot."""
    try:
        bot = FFICryptoNewsBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        log("Bot stopped by user")
    except Exception as e:
        log(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()

