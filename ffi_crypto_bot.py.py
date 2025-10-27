#!/usr/bin/env python3
"""
FFI Crypto News Bot - Multi-Discord Edition with German Translation
Advanced cryptocurrency news aggregator with dual-language support
"""

import asyncio
import aiohttp
import feedparser
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Simple print-based logging to avoid encoding issues
def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - {message}")

class FFICryptoNewsBot:
    """Advanced crypto news bot with German translation and multi-Discord support."""
    
    def __init__(self):
        """Initialize the FFI Crypto News Bot."""
        self.config = {
            'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
            'discord_webhook': os.getenv('DISCORD_WEBHOOK_URL', ''),
            'discord_webhook_ffi': os.getenv('DISCORD_WEBHOOK_FFI', ''),
            'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
            'max_articles': int(os.getenv('MAX_ARTICLES_PER_RUN', '8')),
            'hours_lookback': int(os.getenv('HOURS_LOOKBACK', '3'))
        }
        
        # Collect all Discord webhooks
        self.discord_webhooks = []
        if self.config['discord_webhook']:
            self.discord_webhooks.append(('Original Discord', self.config['discord_webhook']))
        if self.config['discord_webhook_ffi']:
            self.discord_webhooks.append(('FFI Discord', self.config['discord_webhook_ffi']))
        
        log(f"Configured {len(self.discord_webhooks)} Discord webhook(s)")
        
        # RSS feeds
        self.rss_feeds = {
            'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
            'cointelegraph': 'https://cointelegraph.com/rss',
            'theblock': 'https://www.theblock.co/rss.xml',
            'decrypt': 'https://decrypt.co/feed',
            'bitcoinist': 'https://bitcoinist.com/feed/',
            'cryptoslate': 'https://cryptoslate.com/feed/'
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
    
    def load_processed_articles(self) -> set:
        """Load previously processed article URLs."""
        try:
            if os.path.exists(self.processed_file):
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('articles', []))
        except Exception as e:
            log(f"Could not load processed articles: {e}")
        return set()
    
    def save_processed_articles(self):
        """Save processed article URLs."""
        try:
            recent_articles = list(self.processed_articles)[-100:]
            data = {
                'articles': recent_articles,
                'last_updated': datetime.now().isoformat()
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
    
    def is_recent(self, published_time: str, hours_back: int = None) -> bool:
        """Check if article was published recently."""
        try:
            if hours_back is None:
                hours_back = self.config['hours_lookback']
            
            pub_time = datetime.fromtimestamp(time.mktime(time.strptime(published_time)))
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            return pub_time > cutoff_time
        except Exception:
            return True
    
    async def fetch_rss_feed(self, session: aiohttp.ClientSession, name: str, url: str) -> List[Dict]:
        """Fetch and parse RSS feed."""
        try:
            log(f"Fetching RSS feed from {name}")
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)
                    
                    articles = []
                    for entry in feed.entries:
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
    
    def analyze_sentiment(self, title: str, description: str) -> Tuple[str, str]:
        """Analyze sentiment of the article."""
        text = f"{title} {description}".lower()
        
        positive_words = ['surge', 'rally', 'bull', 'gain', 'rise', 'up', 'high', 'moon', 
                         'breakthrough', 'adoption', 'partnership', 'launch', 'upgrade']
        
        negative_words = ['crash', 'dump', 'bear', 'fall', 'drop', 'down', 'low', 'hack',
                         'ban', 'regulation', 'concern', 'warning', 'risk', 'decline']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            return 'Bullish', 'green'
        elif negative_count > positive_count:
            return 'Bearish', 'red'
        else:
            return 'Neutral', 'yellow'
    
    def format_article_for_telegram(self, article: Dict, german_title: str = None, german_desc: str = None) -> str:
        """Format article for Telegram."""
        sentiment, _ = self.analyze_sentiment(article['title'], article['description'])
        
        message = f"**{article['title']}**\n\n"
        message += f"{article['description']}\n\n"
        
        if german_title and german_desc and "[" not in german_title:
            message += f"**{german_title}**\n\n"
            message += f"{german_desc}\n\n"
        
        message += f"Sentiment: {sentiment}\n"
        message += f"Source: {article['source'].title()}\n"
        message += f"[Read More]({article['link']})"
        
        return message
    
    def format_article_for_discord(self, article: Dict, german_title: str = None, german_desc: str = None) -> Dict:
        """Format article for Discord webhook."""
        sentiment, color_indicator = self.analyze_sentiment(article['title'], article['description'])
        
        color_map = {'green': 0x00ff00, 'red': 0xff0000, 'yellow': 0xffff00}
        embed_color = color_map.get(color_indicator, 0x0099ff)
        
        description = f"**English:** {article['description']}\n\n"
        if german_title and german_desc and "[" not in german_title:
            description += f"**Deutsch:** {german_desc}"
        
        embed = {
            "embeds": [{
                "title": article['title'],
                "description": description,
                "url": article['link'],
                "color": embed_color,
                "fields": [
                    {
                        "name": "Sentiment",
                        "value": sentiment,
                        "inline": True
                    },
                    {
                        "name": "Source", 
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
        
        if german_title and "[" not in german_title:
            embed["embeds"][0]["fields"].insert(0, {
                "name": "German Title",
                "value": german_title,
                "inline": False
            })
        
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
        
        log(f"Processing {len(articles)} articles with German translation")
        log(f"Will deliver to: {len(self.discord_webhooks)} Discord server(s) + Telegram")
        
        for article in articles:
            try:
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
        log("FFI CRYPTO NEWS BOT - MULTI-DISCORD EDITION")
        log("Dual-Language (English + German) - Multi-Platform Delivery")
        log("=" * 80)
        log(f"Discord Servers: {len(self.discord_webhooks)}")
        log(f"Telegram: {'Enabled' if self.config['telegram_token'] else 'Disabled'}")
        log(f"German Translation: {'Enabled (OpenAI)' if self.config['openai_api_key'] else 'Disabled'}")
        log("=" * 80)
        
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
            
            log(f"Found {len(all_articles)} total new articles")
            log(f"Processing top {len(articles_to_process)} articles")
            
            # Process and send articles
            await self.process_articles(articles_to_process)
            
            # Save processed articles
            self.save_processed_articles()
            
            log("=" * 80)
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

