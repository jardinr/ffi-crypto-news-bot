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
            'hours_lookback': int(os.getenv('HOURS_LOOKBACK', '3')),
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
                        if (entry.link not in self.processed_articles and
                            self.is_crypto_related(entry.title, getattr(entry, 'summary', '')) and
                            self.is_recent(getattr(entry, 'published', ''))):
                            
                            article = {
                                'title': entry.title,
                                'link': entry.link,
                                'description': getattr(entry, 'summary', '')[:300],
                                'source': name,
                                'published': getattr(entry, 'published', ''),
                                'credibility': credibility
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
        """Format article for Telegram with Module 8 significance indicators."""
        stars = '⭐' * article['credibility']
        
        # Translate classification to German
        classification_de = {
            'High Impact': 'HOHE BEDEUTUNG',
            'Medium Impact': 'MITTLERE BEDEUTUNG',
            'Low Impact': 'GERINGE BEDEUTUNG'
        }.get(article['classification'], article['classification'].upper())
        
        message = f"{article['classification_emoji']} **{classification_de}**\n\n"
        # Use German title if available, otherwise English
        display_title = german_title if (german_title and "[" not in german_title) else article['title']
        display_desc = german_desc if (german_desc and "[" not in german_desc) else article['description']
        
        message += f"**{display_title}**\n\n"
        # Translate sentiment to German
        sentiment_de = {
            'Bullish': 'Bullisch',
            'Bearish': 'Bärisch',
            'Neutral': 'Neutral'
        }.get(article['sentiment_label'], article['sentiment_label'])
        
        message += f"📊 Bedeutung: {article['total_score']}/5\n"
        message += f"⭐ Glaubwürdigkeit: {stars} ({article['credibility']}/5)\n"
        message += f"📈 Marktauswirkung: {article['market_impact']}/5\n"
        message += f"🎯 Relevanz: {article['relevance']}/5\n"
        message += f"💭 Stimmung: {sentiment_de} ({article['sentiment_score']:+d})\n"
        message += f"⏰ Zeitliche Dringlichkeit: {article['time_impact']}/5\n\n"
        
        message += f"{display_desc}\n\n"
        
        message += f"Quelle: {article['source']} | [Mehr lesen]({article['link']})"
        
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

