#!/usr/bin/env python3
"""
FFI Crypto News Bot - Financial Freedom Institute
Advanced cryptocurrency news aggregator with AI-powered analysis.

Built to replace unreliable n8n workflows with a fast, reliable Python solution.
"""

import asyncio
import aiohttp
import feedparser
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib

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
    """FFI Crypto News Bot - Superior alternative to n8n workflows."""
    
    def __init__(self):
        """Initialize the bot with configuration."""
        self.config = self.load_config()
        self.session = None
        self.processed_articles = set()
        self.load_processed_articles()
        
        # Premium RSS Feed Sources
        self.rss_sources = {
            'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
            'cointelegraph': 'https://cointelegraph.com/rss',
            'theblock': 'https://www.theblock.co/api/rss',
            'decrypt': 'https://decrypt.co/feed',
            'bitcoinist': 'https://bitcoinist.com/feed/',
            'cryptoslate': 'https://cryptoslate.com/feed/',
            'newsbtc': 'https://www.newsbtc.com/feed/',
            'coinjournal': 'https://coinjournal.net/feed/',
            'cryptonews': 'https://cryptonews.com/news/feed/'
        }
        
        # Enhanced crypto keywords for intelligent filtering
        self.crypto_keywords = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
            'blockchain', 'defi', 'nft', 'altcoin', 'trading', 'whale',
            'market', 'price', 'bull', 'bear', 'hodl', 'mining', 'staking',
            'solana', 'cardano', 'polkadot', 'chainlink', 'uniswap', 'aave',
            'binance', 'coinbase', 'kraken', 'doge', 'shib', 'matic',
            'avalanche', 'terra', 'luna', 'atom', 'dot', 'ada', 'link', 'uni',
            'web3', 'metaverse', 'dao', 'yield', 'liquidity', 'swap', 'dex'
        ]
        
        # Market sentiment indicators
        self.bullish_keywords = ['surge', 'rally', 'pump', 'moon', 'bullish', 'gains', 'rise', 'up', 'soar', 'rocket']
        self.bearish_keywords = ['crash', 'dump', 'bearish', 'fall', 'drop', 'decline', 'down', 'plunge', 'tank']
    
    def load_config(self) -> Dict[str, str]:
        """Load configuration from environment variables."""
        return {
            'discord_webhook': os.getenv('DISCORD_WEBHOOK_URL', ''),
            'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
            'max_articles_per_run': int(os.getenv('MAX_ARTICLES_PER_RUN', '8')),
            'hours_lookback': int(os.getenv('HOURS_LOOKBACK', '3'))
        }
    
    def load_processed_articles(self):
        """Load previously processed article IDs to avoid duplicates."""
        try:
            if os.path.exists('processed_articles.json'):
                with open('processed_articles.json', 'r') as f:
                    data = json.load(f)
                    self.processed_articles = set(data.get('articles', []))
                    logger.info(f"📚 Loaded {len(self.processed_articles)} processed articles")
        except Exception as e:
            logger.error(f"Error loading processed articles: {e}")
    
    def save_processed_articles(self):
        """Save processed article IDs to prevent reprocessing."""
        try:
            # Keep only recent articles (last 7 days worth)
            cutoff_time = time.time() - (7 * 24 * 3600)
            recent_articles = {
                article_id for article_id in self.processed_articles
                if self.get_article_timestamp(article_id) > cutoff_time
            }
            
            with open('processed_articles.json', 'w') as f:
                json.dump({'articles': list(recent_articles)}, f)
            
            self.processed_articles = recent_articles
            logger.info(f"💾 Saved {len(recent_articles)} recent processed articles")
        except Exception as e:
            logger.error(f"Error saving processed articles: {e}")
    
    def get_article_timestamp(self, article_id: str) -> float:
        """Extract timestamp from article ID."""
        try:
            if '_' in article_id:
                timestamp_str = article_id.split('_')[-1]
                return float(timestamp_str)
        except:
            pass
        return time.time()
    
    def generate_article_id(self, article: Dict[str, Any]) -> str:
        """Generate unique ID for article."""
        content = f"{article.get('title', '')}{article.get('link', '')}"
        hash_id = hashlib.md5(content.encode()).hexdigest()[:12]
        timestamp = str(int(time.time()))
        return f"{hash_id}_{timestamp}"
    
    def is_crypto_relevant(self, text: str) -> bool:
        """Check if text contains crypto-relevant keywords."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.crypto_keywords)
    
    def analyze_sentiment(self, text: str) -> str:
        """Advanced sentiment analysis based on market keywords."""
        text_lower = text.lower()
        
        bullish_count = sum(1 for keyword in self.bullish_keywords if keyword in text_lower)
        bearish_count = sum(1 for keyword in self.bearish_keywords if keyword in text_lower)
        
        if bullish_count > bearish_count:
            return "📈 Bullish"
        elif bearish_count > bullish_count:
            return "📉 Bearish"
        else:
            return "➡️ Neutral"
    
    def extract_cryptocurrencies(self, text: str) -> List[str]:
        """Extract mentioned cryptocurrencies from text."""
        text_lower = text.lower()
        found_cryptos = []
        
        crypto_map = {
            'bitcoin': 'BTC', 'btc': 'BTC',
            'ethereum': 'ETH', 'eth': 'ETH',
            'solana': 'SOL', 'sol': 'SOL',
            'cardano': 'ADA', 'ada': 'ADA',
            'polkadot': 'DOT', 'dot': 'DOT',
            'chainlink': 'LINK', 'link': 'LINK',
            'dogecoin': 'DOGE', 'doge': 'DOGE',
            'shiba': 'SHIB', 'shib': 'SHIB',
            'polygon': 'MATIC', 'matic': 'MATIC',
            'avalanche': 'AVAX', 'avax': 'AVAX',
            'uniswap': 'UNI', 'uni': 'UNI',
            'aave': 'AAVE'
        }
        
        for keyword, symbol in crypto_map.items():
            if keyword in text_lower and symbol not in found_cryptos:
                found_cryptos.append(symbol)
        
        return found_cryptos[:3]  # Limit to 3 cryptos
    
    async def fetch_rss_feed(self, source_name: str, url: str) -> List[Dict[str, Any]]:
        """Fetch and parse RSS feed from a source."""
        try:
            logger.info(f"🔍 Fetching RSS feed from {source_name}")
            
            async with self.session.get(url, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)
                    
                    articles = []
                    cutoff_time = datetime.now() - timedelta(hours=self.config['hours_lookback'])
                    
                    for entry in feed.entries[:10]:  # Limit entries per source
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
                            
                            # Extract article data
                            article = {
                                'source': source_name,
                                'title': entry.get('title', ''),
                                'link': entry.get('link', ''),
                                'description': entry.get('description', ''),
                                'published': pub_date.isoformat() if pub_date else datetime.now().isoformat(),
                                'author': entry.get('author', ''),
                                'tags': [tag.term for tag in entry.get('tags', [])]
                            }
                            
                            # Check if crypto-relevant
                            full_text = f"{article['title']} {article['description']}"
                            if self.is_crypto_relevant(full_text):
                                article_id = self.generate_article_id(article)
                                if article_id not in self.processed_articles:
                                    # Add AI analysis
                                    article['id'] = article_id
                                    article['sentiment'] = self.analyze_sentiment(full_text)
                                    article['cryptocurrencies'] = self.extract_cryptocurrencies(full_text)
                                    
                                    articles.append(article)
                                    self.processed_articles.add(article_id)
                        
                        except Exception as e:
                            logger.error(f"Error processing entry from {source_name}: {e}")
                            continue
                    
                    logger.info(f"✅ Found {len(articles)} new crypto articles from {source_name}")
                    return articles
                
                else:
                    logger.warning(f"⚠️ Failed to fetch {source_name}: HTTP {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"❌ Error fetching RSS from {source_name}: {e}")
            return []
    
    def format_article_for_discord(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Format article for Discord webhook."""
        title = article['title'][:100] + "..." if len(article['title']) > 100 else article['title']
        description = article['description'][:300] + "..." if len(article['description']) > 300 else article['description']
        
        # Get color based on sentiment
        color_map = {
            '📈 Bullish': 0x00ff00,  # Green
            '📉 Bearish': 0xff0000,  # Red
            '➡️ Neutral': 0xffff00   # Yellow
        }
        color = color_map.get(article.get('sentiment', '➡️ Neutral'), 0xffff00)
        
        # Create embed
        embed = {
            'title': title,
            'url': article['link'],
            'description': description,
            'color': color,
            'timestamp': article['published'],
            'footer': {'text': f"FFI Crypto Bot • {article['source'].title()}"},
            'fields': [
                {'name': '📊 Sentiment', 'value': article.get('sentiment', 'N/A'), 'inline': True}
            ]
        }
        
        # Add cryptocurrencies if found
        if article.get('cryptocurrencies'):
            embed['fields'].append({
                'name': '💰 Cryptocurrencies',
                'value': ', '.join(article['cryptocurrencies']),
                'inline': True
            })
        
        return {'embeds': [embed]}
    
    def format_article_for_telegram(self, article: Dict[str, Any]) -> str:
        """Format article for Telegram."""
        title = article['title']
        source = article['source'].title()
        link = article['link']
        sentiment = article.get('sentiment', '➡️ Neutral')
        
        message = f"🚀 *{title}*\n\n"
        message += f"{sentiment}\n"
        
        # Add cryptocurrencies if found
        if article.get('cryptocurrencies'):
            message += f"💰 *Coins:* {', '.join(article['cryptocurrencies'])}\n"
        
        message += f"\n📰 *Source:* {source}\n"
        message += f"🔗 [Read More]({link})\n"
        message += f"\n_Powered by FFI Crypto Bot_ 🤖"
        
        return message
    
    async def send_to_discord(self, articles: List[Dict[str, Any]]):
        """Send articles to Discord webhook."""
        if not self.config['discord_webhook']:
            logger.info("💬 Discord webhook not configured, skipping Discord delivery")
            return
        
        try:
            for article in articles:
                payload = self.format_article_for_discord(article)
                
                async with self.session.post(
                    self.config['discord_webhook'],
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 204:
                        logger.info(f"📤 Sent to Discord: {article['title'][:50]}...")
                    else:
                        logger.error(f"❌ Discord webhook failed: HTTP {response.status}")
                
                # Rate limiting
                await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"❌ Error sending to Discord: {e}")
    
    async def send_to_telegram(self, articles: List[Dict[str, Any]]):
        """Send articles to Telegram."""
        if not self.config['telegram_bot_token'] or not self.config['telegram_chat_id']:
            logger.warning("⚠️ Telegram configuration incomplete")
            return
        
        try:
            url = f"https://api.telegram.org/bot{self.config['telegram_bot_token']}/sendMessage"
            
            for article in articles:
                message = self.format_article_for_telegram(article)
                
                payload = {
                    'chat_id': self.config['telegram_chat_id'],
                    'text': message,
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': False
                }
                
                async with self.session.post(url, json=payload, timeout=30) as response:
                    if response.status == 200:
                        logger.info(f"📱 Sent to Telegram: {article['title'][:50]}...")
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Telegram API failed: HTTP {response.status} - {error_text}")
                
                # Rate limiting
                await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"❌ Error sending to Telegram: {e}")
    
    async def run(self):
        """Main execution function - The heart of FFI Crypto Bot."""
        logger.info("🚀 Starting FFI Crypto News Bot - Superior to n8n!")
        
        # Create aiohttp session
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=5)
        self.session = aiohttp.ClientSession(connector=connector)
        
        try:
            # Fetch articles from all RSS sources concurrently
            all_articles = []
            
            tasks = [
                self.fetch_rss_feed(source_name, url)
                for source_name, url in self.rss_sources.items()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_articles.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"❌ RSS fetch error: {result}")
            
            if not all_articles:
                logger.info("📭 No new crypto articles found")
                return
            
            # Sort by publication date (newest first)
            all_articles.sort(key=lambda x: x['published'], reverse=True)
            
            # Limit articles per run
            articles_to_process = all_articles[:self.config['max_articles_per_run']]
            
            logger.info(f"⚡ Processing {len(articles_to_process)} articles")
            
            # Send to platforms simultaneously
            await asyncio.gather(
                self.send_to_discord(articles_to_process),
                self.send_to_telegram(articles_to_process)
            )
            
            # Save processed articles
            self.save_processed_articles()
            
            logger.info(f"✅ Successfully processed {len(articles_to_process)} articles")
            
            # Log summary
            sources_summary = {}
            sentiment_summary = {}
            
            for article in articles_to_process:
                source = article['source']
                sentiment = article.get('sentiment', '➡️ Neutral')
                
                sources_summary[source] = sources_summary.get(source, 0) + 1
                sentiment_summary[sentiment] = sentiment_summary.get(sentiment, 0) + 1
            
            logger.info(f"📊 Articles by source: {sources_summary}")
            logger.info(f"📈 Sentiment breakdown: {sentiment_summary}")
            logger.info("🎉 FFI Crypto Bot execution completed successfully!")
        
        except Exception as e:
            logger.error(f"❌ Error in main execution: {e}")
        
        finally:
            await self.session.close()

async def main():
    """Entry point for FFI Crypto News Bot."""
    bot = FFICryptoBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
