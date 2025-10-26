#!/usr/bin/env python3
"""
FFI Crypto News Bot with German Translation - Multi-Discord Support
Advanced cryptocurrency news aggregator with dual-language support
Supports multiple Discord webhooks for different servers
"""

import asyncio
import aiohttp
import feedparser
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ffi_crypto_bot.log')
    ]
)
logger = logging.getLogger(__name__)

class FFICryptoNewsBot:
    """Advanced crypto news bot with German translation and multi-Discord support."""
    
    def __init__(self):
        """Initialize the FFI Crypto News Bot with dual-language and multi-platform support."""
        self.config = {
            'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
            'discord_webhook': os.getenv('DISCORD_WEBHOOK_URL', ''),  # Original webhook
            'discord_webhook_ffi': os.getenv('DISCORD_WEBHOOK_FFI', ''),  # New FFI server webhook
            'gemini_api_key': os.getenv('GEMINI_API_KEY', ''),
            'max_articles': int(os.getenv('MAX_ARTICLES_PER_RUN', '8')),
            'hours_lookback': int(os.getenv('HOURS_LOOKBACK', '3'))
        }
        
        # Collect all Discord webhooks into a list
        self.discord_webhooks = []
        if self.config['discord_webhook']:
            self.discord_webhooks.append(('Original Discord', self.config['discord_webhook']))
        if self.config['discord_webhook_ffi']:
            self.discord_webhooks.append(('FFI Discord', self.config['discord_webhook_ffi']))
        
        logger.info(f"🎯 Configured {len(self.discord_webhooks)} Discord webhook(s)")
        
        # RSS feeds for crypto news
        self.rss_feeds = {
            'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
            'cointelegraph': 'https://cointelegraph.com/rss',
            'theblock': 'https://www.theblock.co/rss.xml',
            'decrypt': 'https://decrypt.co/feed',
            'bitcoinist': 'https://bitcoinist.com/feed/',
            'cryptoslate': 'https://cryptoslate.com/feed/'
        }
        
        # Crypto-related keywords for filtering
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
        
        logger.info(f"📚 Loaded {len(self.processed_articles)} processed articles")
    
    def load_processed_articles(self) -> set:
        """Load previously processed article URLs."""
        try:
            if os.path.exists(self.processed_file):
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('articles', []))
        except Exception as e:
            logger.warning(f"⚠️ Could not load processed articles: {e}")
        return set()
    
    def save_processed_articles(self):
        """Save processed article URLs."""
        try:
            # Keep only recent articles (last 100)
            recent_articles = list(self.processed_articles)[-100:]
            data = {
                'articles': recent_articles,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.processed_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"💾 Saved {len(recent_articles)} recent processed articles")
        except Exception as e:
            logger.error(f"❌ Could not save processed articles: {e}")
    
    def is_crypto_related(self, title: str, description: str = '') -> bool:
        """Check if article is cryptocurrency-related."""
        text = f"{title} {description}".lower()
        return any(keyword in text for keyword in self.crypto_keywords)
    
    def is_recent(self, published_time: str, hours_back: int = None) -> bool:
        """Check if article was published recently."""
        try:
            if hours_back is None:
                hours_back = self.config['hours_lookback']
            
            # Parse the published time
            pub_time = datetime.fromtimestamp(time.mktime(time.strptime(published_time)))
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            return pub_time > cutoff_time
        except Exception:
            # If we can't parse the time, assume it's recent
            return True
    
    async def fetch_rss_feed(self, session: aiohttp.ClientSession, name: str, url: str) -> List[Dict]:
        """Fetch and parse RSS feed."""
        try:
            logger.info(f"🔍 Fetching RSS feed from {name}")
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)
                    
                    articles = []
                    for entry in feed.entries:
                        # Check if article is new and crypto-related
                        if (entry.link not in self.processed_articles and
                            self.is_crypto_related(entry.title, getattr(entry, 'summary', '')) and
                            self.is_recent(getattr(entry, 'published', ''))):
                            
                            articles.append({
                                'title': entry.title,
                                'link': entry.link,
                                'description': getattr(entry, 'summary', '')[:300],
                                'source': name,
                                'published': getattr(entry, 'published', '')
                            })
                    
                    logger.info(f"✅ Found {len(articles)} new crypto articles from {name}")
                    return articles
                else:
                    logger.warning(f"⚠️ Failed to fetch {name}: HTTP {response.status}")
        except Exception as e:
            logger.error(f"❌ Error fetching {name}: {e}")
        return []
    
    async def translate_to_german(self, text: str) -> str:
        """Translate text to German using Gemini AI."""
        try:
            if not self.config['gemini_api_key']:
                logger.warning("💬 Gemini API key not configured, skipping German translation")
                return f"[German translation unavailable]"
            
            # Use Gemini API for translation
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.config['gemini_api_key']}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"Translate the following cryptocurrency news text to German. Keep technical terms and proper nouns in their original form when appropriate. Provide only the German translation without any additional text:\n\n{text}"
                    }]
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        result = await response.json()
                        german_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                        return german_text
                    else:
                        logger.error(f"❌ Gemini translation failed: HTTP {response.status}")
                        return "[Translation failed]"
        except Exception as e:
            logger.error(f"❌ Translation error: {e}")
            return "[Translation error]"
    
    def analyze_sentiment(self, title: str, description: str) -> Tuple[str, str]:
        """Analyze sentiment of the article."""
        text = f"{title} {description}".lower()
        
        # Positive indicators
        positive_words = ['surge', 'rally', 'bull', 'gain', 'rise', 'up', 'high', 'moon', 
                         'breakthrough', 'adoption', 'partnership', 'launch', 'upgrade']
        
        # Negative indicators  
        negative_words = ['crash', 'dump', 'bear', 'fall', 'drop', 'down', 'low', 'hack',
                         'ban', 'regulation', 'concern', 'warning', 'risk', 'decline']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            return '📈 Bullish', '🟢'
        elif negative_count > positive_count:
            return '📉 Bearish', '🔴'
        else:
            return '➡️ Neutral', '🟡'
    
    def format_article_for_telegram(self, article: Dict, german_title: str = None, german_desc: str = None) -> str:
        """Format article for Telegram with dual-language support."""
        sentiment, _ = self.analyze_sentiment(article['title'], article['description'])
        
        # Format English version
        message = f"🚀 **{article['title']}**\n\n"
        message += f"📰 {article['description']}\n\n"
        
        # Add German translation if available
        if german_title and german_desc and "[" not in german_title:
            message += f"🇩🇪 **{german_title}**\n\n"
            message += f"📰 {german_desc}\n\n"
        
        message += f"📊 Sentiment: {sentiment}\n"
        message += f"📍 Source: {article['source'].title()}\n"
        message += f"🔗 [Read More]({article['link']})"
        
        return message
    
    def format_article_for_discord(self, article: Dict, german_title: str = None, german_desc: str = None) -> Dict:
        """Format article for Discord webhook with dual-language support."""
        sentiment, color_indicator = self.analyze_sentiment(article['title'], article['description'])
        
        # Color mapping for Discord embeds
        color_map = {'🟢': 0x00ff00, '🔴': 0xff0000, '🟡': 0xffff00}
        embed_color = color_map.get(color_indicator, 0x0099ff)
        
        # Create description with both languages
        description = f"**English:** {article['description']}\n\n"
        if german_title and german_desc and "[" not in german_title:
            description += f"**🇩🇪 Deutsch:** {german_desc}"
        
        embed = {
            "embeds": [{
                "title": article['title'],
                "description": description,
                "url": article['link'],
                "color": embed_color,
                "fields": [
                    {
                        "name": "📊 Sentiment",
                        "value": sentiment,
                        "inline": True
                    },
                    {
                        "name": "📍 Source", 
                        "value": article['source'].title(),
                        "inline": True
                    }
                ],
                "footer": {
                    "text": f"FFI Crypto News Bot • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                },
                "timestamp": datetime.now().isoformat()
            }]
        }
        
        # Add German title as field if available
        if german_title and "[" not in german_title:
            embed["embeds"][0]["fields"].insert(0, {
                "name": "🇩🇪 German Title",
                "value": german_title,
                "inline": False
            })
        
        return embed
    
    async def send_to_telegram(self, message: str):
        """Send message to Telegram."""
        if not self.config['telegram_token'] or not self.config['telegram_chat_id']:
            logger.info("💬 Telegram not configured, skipping Telegram delivery")
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
                        logger.info("📱 Sent to Telegram: " + message.split('\n')[0][:50] + "...")
                    else:
                        logger.error(f"❌ Telegram failed: HTTP {response.status}")
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
    
    async def send_to_all_discord_webhooks(self, embed_data: Dict):
        """Send embed to ALL configured Discord webhooks."""
        if not self.discord_webhooks:
            logger.info("💬 No Discord webhooks configured, skipping Discord delivery")
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
                            logger.info(f"📤 Sent to {webhook_name}: {title}...")
                        else:
                            logger.error(f"❌ {webhook_name} failed: HTTP {response.status}")
            except Exception as e:
                logger.error(f"❌ {webhook_name} error: {e}")
            
            # Small delay between webhooks to avoid rate limiting
            await asyncio.sleep(0.3)
    
    async def process_articles(self, articles: List[Dict]):
        """Process articles with German translation and send to all platforms."""
        if not articles:
            logger.info("📭 No new articles to process")
            return
        
        logger.info(f"⚡ Processing {len(articles)} articles with German translation")
        logger.info(f"🎯 Will deliver to: {len(self.discord_webhooks)} Discord server(s) + Telegram")
        
        for article in articles:
            try:
                # Translate title and description to German
                german_title = await self.translate_to_german(article['title'])
                await asyncio.sleep(0.5)  # Rate limiting for Gemini API
                
                german_desc = await self.translate_to_german(article['description'])
                await asyncio.sleep(0.5)  # Rate limiting for Gemini API
                
                # Format for both platforms
                telegram_message = self.format_article_for_telegram(article, german_title, german_desc)
                discord_embed = self.format_article_for_discord(article, german_title, german_desc)
                
                # Send to ALL Discord webhooks
                await self.send_to_all_discord_webhooks(discord_embed)
                await asyncio.sleep(0.5)  # Rate limiting between platforms
                
                # Send to Telegram
                await self.send_to_telegram(telegram_message)
                await asyncio.sleep(0.5)  # Rate limiting
                
                # Mark as processed
                self.processed_articles.add(article['link'])
                
            except Exception as e:
                logger.error(f"❌ Error processing article {article['title']}: {e}")
    
    async def run(self):
        """Main execution function."""
        logger.info("=" * 80)
        logger.info("🚀 FFI CRYPTO NEWS BOT - MULTI-DISCORD EDITION")
        logger.info("   Dual-Language (English + German) • Multi-Platform Delivery")
        logger.info("=" * 80)
        logger.info(f"📡 Discord Servers: {len(self.discord_webhooks)}")
        logger.info(f"📱 Telegram: {'✅ Enabled' if self.config['telegram_token'] else '❌ Disabled'}")
        logger.info(f"🌍 German Translation: {'✅ Enabled' if self.config['gemini_api_key'] else '❌ Disabled'}")
        logger.info("=" * 80)
        
        try:
            # Fetch articles from all RSS feeds
            async with aiohttp.ClientSession() as session:
                tasks = [self.fetch_rss_feed(session, name, url) for name, url in self.rss_feeds.items()]
                results = await asyncio.gather(*tasks)
            
            # Flatten and sort articles
            all_articles = [article for sublist in results for article in sublist]
            all_articles.sort(key=lambda x: x.get('published', ''), reverse=True)
            
            # Limit to max articles
            articles_to_process = all_articles[:self.config['max_articles']]
            
            logger.info(f"📊 Found {len(all_articles)} total new articles")
            logger.info(f"📝 Processing top {len(articles_to_process)} articles")
            
            # Process and send articles
            await self.process_articles(articles_to_process)
            
            # Save processed articles
            self.save_processed_articles()
            
            logger.info("=" * 80)
            logger.info("✅ FFI CRYPTO NEWS BOT COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ Critical error in main execution: {e}")
            raise

def main():
    """Entry point for the bot."""
    try:
        bot = FFICryptoNewsBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("⚠️ Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()

