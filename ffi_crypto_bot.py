#!/usr/bin/env python3
"""
FFI Crypto News Bot - RSS Edition
Advanced cryptocurrency news aggregator with RSS feeds and German translation.

Features:
- RSS feeds (CoinDesk, Watcher Guru, Insider Paper)
- German translation via Google Gemini AI
- Content filtering and deduplication
- Dual-language delivery to Discord and Telegram
"""

import asyncio
import aiohttp
import feedparser
import json
import logging
import os
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ffi_crypto_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FFICryptoBot:
    """FFI Crypto News Bot with RSS feeds and German translation."""
    
    def __init__(self):
        """Initialize the bot with configuration."""
        self.config = self.load_config()
        self.session = None
        self.processed_articles = set()
        self.load_processed_articles()
        
        # RSS Feed Sources
        self.rss_sources = {
            'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
            'watcher_guru': 'https://watcher.guru/news/feed',
            'insider_paper': 'https://insiderpaper.com/feed/'
        }
        
        # Enhanced crypto keywords for intelligent filtering
        self.crypto_keywords = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
            'blockchain', 'defi', 'nft', 'altcoin', 'trading', 'whale',
            'market', 'price', 'bull', 'bear', 'hodl', 'mining', 'staking',
            'solana', 'cardano', 'polkadot', 'chainlink', 'uniswap', 'aave',
            'binance', 'coinbase', 'kraken', 'doge', 'shib', 'matic',
            'avalanche', 'terra', 'luna', 'atom', 'dot', 'ada', 'link', 'uni',
            'web3', 'metaverse', 'dao', 'yield', 'liquidity', 'swap', 'dex',
            'xrp', 'ripple', 'usdt', 'usdc', 'stablecoin', 'token', 'coin'
        ]
        
        # Market sentiment indicators
        self.bullish_keywords = ['surge', 'rally', 'pump', 'moon', 'bullish', 'gains', 'rise', 'up', 'soar', 'rocket', 'breakout']
        self.bearish_keywords = ['crash', 'dump', 'bearish', 'fall', 'drop', 'decline', 'down', 'plunge', 'tank', 'collapse']
        
        # German sentiment translations
        self.sentiment_german = {
            '📈 Bullish': '📈 Bullisch',
            '📉 Bearish': '📉 Bärisch',
            '➡️ Neutral': '➡️ Neutral'
        }
    
    def load_config(self) -> Dict[str, str]:
        """Load configuration from environment variables."""
        return {
            'discord_webhook': os.getenv('DISCORD_WEBHOOK_URL', ''),
            'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
            'gemini_api_key': os.getenv('GEMINI_API_KEY', ''),
            'max_articles_per_run': int(os.getenv('MAX_ARTICLES_PER_RUN', '10')),
            'hours_lookback': int(os.getenv('HOURS_LOOKBACK', '3')),
            'enable_german': os.getenv('ENABLE_GERMAN_TRANSLATION', 'true').lower() == 'true'
        }
    
    def load_processed_articles(self):
        """Load previously processed articles from file."""
        try:
            if os.path.exists('processed_articles.json'):
                with open('processed_articles.json', 'r') as f:
                    self.processed_articles = set(json.load(f))
                logger.info(f"📂 Loaded {len(self.processed_articles)} processed articles")
        except Exception as e:
            logger.error(f"❌ Error loading processed articles: {e}")
            self.processed_articles = set()
    
    def save_processed_articles(self):
        """Save processed articles to file."""
        try:
            with open('processed_articles.json', 'w') as f:
                json.dump(list(self.processed_articles), f)
        except Exception as e:
            logger.error(f"❌ Error saving processed articles: {e}")
    
    def generate_article_hash(self, title: str, link: str) -> str:
        """Generate unique hash for article deduplication."""
        content = f"{title}{link}".lower()
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_crypto_related(self, text: str) -> bool:
        """Check if text is crypto-related."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.crypto_keywords)
    
    def analyze_sentiment(self, text: str) -> str:
        """Analyze market sentiment from text."""
        text_lower = text.lower()
        bullish_count = sum(1 for keyword in self.bullish_keywords if keyword in text_lower)
        bearish_count = sum(1 for keyword in self.bearish_keywords if keyword in text_lower)
        
        if bullish_count > bearish_count:
            return '📈 Bullish'
        elif bearish_count > bullish_count:
            return '📉 Bearish'
        else:
            return '➡️ Neutral'
    
    def extract_mentioned_coins(self, text: str) -> List[str]:
        """Extract cryptocurrency tickers from text."""
        text_upper = text.upper()
        common_tickers = ['BTC', 'ETH', 'XRP', 'SOL', 'ADA', 'DOT', 'LINK', 'UNI', 'MATIC', 'AVAX', 'DOGE', 'SHIB']
        found_tickers = [ticker for ticker in common_tickers if ticker in text_upper]
        return list(set(found_tickers))[:5]  # Limit to 5 tickers
    
    async def translate_to_german(self, text: str) -> str:
        """Translate text to German using Google Gemini AI."""
        if not self.config['gemini_api_key']:
            logger.warning("⚠️ Gemini API key not configured")
            return ""
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.config['gemini_api_key']}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"Translate the following text to German. Only provide the translation, no explanations:\n\n{text}"
                    }]
                }]
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    german_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                    logger.info("🇩🇪 Translated text successfully")
                    return german_text
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Gemini translation failed: HTTP {response.status}")
                    return ""
        except Exception as e:
            logger.error(f"❌ Translation error: {e}")
            return ""
    
    async def fetch_rss_feed(self, source_name: str, feed_url: str) -> List[Dict[str, Any]]:
        """Fetch and parse RSS feed."""
        try:
            logger.info(f"🔍 Fetching RSS feed from {source_name}")
            
            async with self.session.get(feed_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.error(f"❌ Failed to fetch {source_name}: HTTP {response.status}")
                    return []
                
                content = await response.text()
                feed = feedparser.parse(content)
                
                articles = []
                cutoff_time = datetime.now() - timedelta(hours=self.config['hours_lookback'])
                
                for entry in feed.entries:
                    try:
                        # Parse publication date
                        pub_date = None
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            pub_date = datetime(*entry.published_parsed[:6])
                        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            pub_date = datetime(*entry.updated_parsed[:6])
                        
                        # Skip old articles
                        if pub_date and pub_date < cutoff_time:
                            continue
                        
                        title = entry.get('title', '').strip()
                        link = entry.get('link', '').strip()
                        description = entry.get('summary', entry.get('description', '')).strip()
                        
                        # Skip if not crypto-related
                        full_text = f"{title} {description}"
                        if not self.is_crypto_related(full_text):
                            continue
                        
                        # Check for duplicates
                        article_hash = self.generate_article_hash(title, link)
                        if article_hash in self.processed_articles:
                            continue
                        
                        articles.append({
                            'title': title,
                            'link': link,
                            'description': description,
                            'source': source_name,
                            'pub_date': pub_date,
                            'hash': article_hash
                        })
                    
                    except Exception as e:
                        logger.error(f"❌ Error parsing entry from {source_name}: {e}")
                        continue
                
                logger.info(f"✅ Found {len(articles)} new crypto articles from {source_name}")
                return articles
        
        except Exception as e:
            logger.error(f"❌ Error fetching RSS feed from {source_name}: {e}")
            return []
    
    async def fetch_all_articles(self) -> List[Dict[str, Any]]:
        """Fetch articles from all RSS sources."""
        all_articles = []
        
        # Fetch from all RSS sources
        for source_name, feed_url in self.rss_sources.items():
            articles = await self.fetch_rss_feed(source_name, feed_url)
            all_articles.extend(articles)
        
        # Sort by publication date (newest first)
        all_articles.sort(key=lambda x: x.get('pub_date') or datetime.min, reverse=True)
        
        # Limit to max articles per run
        return all_articles[:self.config['max_articles_per_run']]
    
    def format_article_for_discord(self, article: Dict[str, Any], german_title: str = "", german_desc: str = "") -> Dict[str, Any]:
        """Format article for Discord webhook."""
        sentiment = self.analyze_sentiment(f"{article['title']} {article['description']}")
        mentioned_coins = self.extract_mentioned_coins(f"{article['title']} {article['description']}")
        
        embed = {
            "title": f"📰 {article['title']}",
            "url": article['link'],
            "description": f"{article['description'][:250]}...",
            "color": 0x4a90e2,  # Blue
            "author": {
                "name": f"Source: {article['source'].replace('_', ' ').title()}",
                "icon_url": "https://i.imgur.com/AJG3K3B.png"
            },
            "fields": [
                {"name": "Sentiment", "value": sentiment, "inline": True},
                {"name": "Mentioned Coins", "value": ', '.join(mentioned_coins) if mentioned_coins else "N/A", "inline": True}
            ],
            "footer": {
                "text": f"FFI Crypto News Bot | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }

        if self.config['enable_german'] and german_title:
            german_sentiment = self.sentiment_german.get(sentiment, sentiment)
            embed['fields'].append({
                "name": "--- 🇩🇪 German Translation ---",
                "value": f"**{german_title}**\n{german_desc[:250]}...",
                "inline": False
            })
            embed['fields'].append({
                "name": "Stimmung", "value": german_sentiment, "inline": True
            })

        return {"embeds": [embed]}

    def format_article_for_telegram(self, article: Dict[str, Any], german_title: str = "", german_desc: str = "") -> str:
        """Format article for Telegram message."""
        sentiment = self.analyze_sentiment(f"{article['title']} {article['description']}")
        mentioned_coins = self.extract_mentioned_coins(f"{article['title']} {article['description']}")
        
        message = (
            f"📰 **{article['title']}**\n\n"
            f"{article['description'][:280]}...\n\n"
            f"**Sentiment:** {sentiment}\n"
            f"**Mentioned Coins:** {', '.join(mentioned_coins) if mentioned_coins else 'N/A'}\n"
            f"**Source:** {article['source'].replace('_', ' ').title()}\n"
            f"[Read More]({article['link']})"
        )

        if self.config['enable_german'] and german_title:
            german_sentiment = self.sentiment_german.get(sentiment, sentiment)
            message += (
                f"\n\n--- 🇩🇪 German Translation ---\n"
                f"**{german_title}**\n"
                f"{german_desc[:280]}...\n\n"
                f"**Stimmung:** {german_sentiment}"
            )

        return message

    async def send_to_discord(self, payload: Dict[str, Any]):
        """Send message to Discord webhook."""
        if not self.config['discord_webhook']:
            logger.warning("⚠️ Discord webhook not configured")
            return
        
        try:
            async with self.session.post(self.config['discord_webhook'], json=payload) as response:
                if response.status in [200, 204]:
                    logger.info("✅ Sent to Discord")
                else:
                    logger.error(f"❌ Discord error: HTTP {response.status}")
        except Exception as e:
            logger.error(f"❌ Error sending to Discord: {e}")

    async def send_to_telegram(self, message: str):
        """Send message to Telegram."""
        if not self.config['telegram_bot_token'] or not self.config['telegram_chat_id']:
            logger.warning("⚠️ Telegram bot not configured")
            return
        
        try:
            url = f"https://api.telegram.org/bot{self.config['telegram_bot_token']}/sendMessage"
            payload = {
                'chat_id': self.config['telegram_chat_id'],
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info("✅ Sent to Telegram")
                else:
                    logger.error(f"❌ Telegram error: HTTP {response.status}")
        except Exception as e:
            logger.error(f"❌ Error sending to Telegram: {e}")

    async def process_article(self, article: Dict[str, Any]):
        """Process and send a single article."""
        try:
            # Translate to German if enabled
            german_title = ""
            german_desc = ""
            
            if self.config['enable_german']:
                german_title = await self.translate_to_german(article['title'])
                if article['description']:
                    german_desc = await self.translate_to_german(article['description'][:500])
            
            # Send to Discord
            discord_payload = self.format_article_for_discord(article, german_title, german_desc)
            await self.send_to_discord(discord_payload)
            
            # Send to Telegram
            telegram_message = self.format_article_for_telegram(article, german_title, german_desc)
            await self.send_to_telegram(telegram_message)
            
            # Mark as processed
            self.processed_articles.add(article['hash'])
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Error processing article {article['link']}: {e}")

    async def run(self):
        """Run the bot."""
        logger.info("🚀 Starting FFI Crypto News Bot")
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            # Fetch all articles
            articles = await self.fetch_all_articles()
            
            if not articles:
                logger.info("No new articles found. Exiting.")
                return
            
            logger.info(f"📰 Processing {len(articles)} articles")
            
            # Process each article
            for article in articles:
                await self.process_article(article)
            
            # Save processed articles
            self.save_processed_articles()
            
            logger.info("✅ Bot run completed successfully")

if __name__ == "__main__":
    bot = FFICryptoBot()
    asyncio.run(bot.run())

