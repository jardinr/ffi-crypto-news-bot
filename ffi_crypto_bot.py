#!/usr/bin/env python3
"""
FFI Crypto News Bot - Enhanced Edition with Notion Integration
Main orchestrator that runs all modules
"""

import asyncio
import sys
from datetime import datetime

# Import configuration
from config import Config

# Import utilities
from utils.openai_client import OpenAIClient
from utils.discord_poster import DiscordPoster
from utils.discord_poster_v2 import DiscordPosterV2
from utils.telegram_poster import TelegramPoster

# Import modules
from modules.news_analyzer import NewsAnalyzer
from modules.news_summarizer import NewsSummarizer
from modules.etf_tracker import ETFTracker
from modules.portfolio_tracker_v2 import PortfolioTrackerV2

def log(message: str):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - {message}")

async def main():
    """Main execution function."""
    log("=" * 60)
    log("FFI Crypto News Bot - Enhanced Edition (Notion Integration)")
    log("=" * 60)
    
    # Load configuration
    config = Config()
    
    # Validate configuration
    is_valid, errors = config.validate()
    if not is_valid:
        log("Configuration errors:")
        for error in errors:
            log(f"  ✗ {error}")
        sys.exit(1)
    
    log(f"Configuration loaded successfully")
    log(f"Enabled modules: {', '.join(config.get_enabled_modules())}")
    
    # Initialize utilities
    openai_client = OpenAIClient(config.openai_api_key)
    discord_poster = DiscordPoster(config.discord_webhooks)
    discord_poster_v2 = DiscordPosterV2(config.discord_webhooks)
    telegram_poster = TelegramPoster(config.telegram_token, config.telegram_chat_id)
    
    # Track results
    results = {
        'articles': [],
        'summary': None,
        'etf_data': None,
        'portfolio_data': None
    }
    
    # ===== MODULE 1: News Analyzer =====
    if config.enable_news_analyzer:
        try:
            log("Running News Analyzer...")
            news_analyzer = NewsAnalyzer(config, openai_client)
            analyzed_articles = await news_analyzer.run()
            results['articles'] = analyzed_articles
            
            # Post individual articles to Discord/Telegram
            for article in analyzed_articles[:5]:  # Post top 5
                await discord_poster.post_article(article, article['analysis'])
                
                # Also post to Telegram
                telegram_text = f"""📰 **{article['title']}**

Quelle: {article['source']}
Link: {article['link']}

**Zusammenfassung:**
{article['analysis'].get('zusammenfassung', '')}

**Analyse:**
• Bedeutung: {'⭐' * article['analysis'].get('bedeutung', 0)} ({article['analysis'].get('bedeutung', 0)}/5)
• Glaubwürdigkeit: {'⭐' * article['analysis'].get('glaubwürdigkeit', 0)} ({article['analysis'].get('glaubwürdigkeit', 0)}/5)
• Marktauswirkung: {article['analysis'].get('marktauswirkung', 'Neutral')}
• Relevanz: {article['analysis'].get('relevanz', 'Mittel')}
• Stimmung: {article['analysis'].get('stimmung', 'Neutral')}
"""
                await telegram_poster.post_message(telegram_text)
                
                # Delay between posts
                await asyncio.sleep(2)
            
            log(f"✓ Analyzed {len(analyzed_articles)} articles")
                
        except Exception as e:
            log(f"Error in News Analyzer: {e}")
    
    # ===== MODULE 2: News Summarizer =====
    if config.enable_news_summary and results['articles']:
        try:
            log("Running News Summarizer...")
            news_summarizer = NewsSummarizer(config, openai_client)
            summary = await news_summarizer.run(results['articles'])
            results['summary'] = summary
            
            if summary:
                await discord_poster.post_summary(summary)
                await telegram_poster.post_message(summary)
                log("✓ Created news summary")
                
        except Exception as e:
            log(f"Error in News Summarizer: {e}")
    
    # ===== MODULE 3: ETF Tracker =====
    if config.enable_etf_tracker:
        try:
            log("Running ETF Tracker...")
            etf_tracker = ETFTracker(config, openai_client)
            etf_data = await etf_tracker.run()
            results['etf_data'] = etf_data
            
            if etf_data:
                await discord_poster.post_etf_flows(etf_data, etf_data.get('analysis', ''))
                
                # Telegram format
                telegram_text = f"""💰 **Bitcoin ETF-Flüsse**

Datum: {etf_data.get('date', 'Heute')}

**Bitcoin ETFs:**
• Netto-Fluss: {etf_data.get('net_flow', 'N/A')}
• Zuflüsse: {etf_data.get('inflows', 'N/A')}
• Abflüsse: {etf_data.get('outflows', 'N/A')}

💡 **Analyse:**
{etf_data.get('analysis', 'Keine Analyse verfügbar')}
"""
                await telegram_poster.post_message(telegram_text)
                log("✓ Tracked ETF flows")
                
        except Exception as e:
            log(f"Error in ETF Tracker: {e}")
    
    # ===== MODULE 4: Portfolio Tracker V2 (Notion Integration) =====
    if config.enable_portfolio_tracker:
        try:
            log("Running Portfolio Tracker V2 (Notion)...")
            portfolio_tracker = PortfolioTrackerV2(config)
            portfolio_data = await portfolio_tracker.run()
            results['portfolio_data'] = portfolio_data
            
            if portfolio_data:
                # Post full portfolio update
                await discord_poster_v2.post_portfolio_update(portfolio_data)
                
                # Post critical signals separately
                critical_signals = [s for s in portfolio_data['all_signals'] if s['urgency'] in ['critical', 'high']]
                if critical_signals:
                    await discord_poster_v2.post_critical_signals(critical_signals)
                
                # Telegram summary
                summary = portfolio_data['summary']
                telegram_text = f"""📊 **Portfolio-Update**

Coins überwacht: {summary['total_coins']}
Preise abgerufen: {summary['prices_fetched']}

🟢 Kaufgelegenheiten: {summary['buy_opportunities']}
🔴 Verkaufssignale: {summary['exit_signals']}
"""
                
                # Add critical signals to Telegram
                if critical_signals:
                    telegram_text += "\n🚨 **Wichtige Signale:**\n"
                    for signal in critical_signals[:5]:
                        telegram_text += f"• {signal['coin']} ({signal['symbol']}): {signal['message']}\n"
                
                await telegram_poster.post_message(telegram_text)
                log(f"✓ Tracked {summary['total_coins']} coins, {summary['buy_opportunities']} buy opportunities, {summary['exit_signals']} exit signals")
                
        except Exception as e:
            log(f"Error in Portfolio Tracker: {e}")
    
    # ===== Summary =====
    log("=" * 60)
    log("Execution Summary:")
    log(f"  Articles analyzed: {len(results['articles'])}")
    log(f"  Summary created: {'Yes' if results['summary'] else 'No'}")
    log(f"  ETF data fetched: {'Yes' if results['etf_data'] else 'No'}")
    log(f"  Portfolio tracked: {'Yes' if results['portfolio_data'] else 'No'}")
    log("=" * 60)
    log("Bot execution completed successfully!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Bot execution interrupted by user")
        sys.exit(0)
    except Exception as e:
        log(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

