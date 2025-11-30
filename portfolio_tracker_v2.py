"""
Portfolio Tracker Module - Enhanced with Notion Data
Monitors cryptocurrency portfolio with tier-based organization and detailed targets
"""

import csv
import asyncio
import aiohttp
import re
from typing import Dict, List, Optional
from datetime import datetime

class PortfolioTrackerV2:
    """Enhanced portfolio tracker using Notion database structure."""
    
    def __init__(self, config):
        """Initialize portfolio tracker with configuration."""
        self.config = config
        self.portfolio_path = 'data/notion_portfolio.csv'
        self.coingecko_api_key = config.coingecko_api_key
        
        # Tier definitions
        self.tiers = {
            'main': {'emoji': '🏠', 'name': 'Main Tier', 'coins': []},
            'high_risk': {'emoji': '🎰', 'name': 'High Risk Tier', 'coins': []},
            'mid': {'emoji': '⚖️', 'name': 'Mid Tier', 'coins': []},
            'safety': {'emoji': '🪨', 'name': 'Sicherheitspolster', 'coins': []},
            'not_prioritized': {'emoji': '❌', 'name': 'Nicht mehr priorisiert', 'coins': []}
        }
        
    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse price string to float, handling various formats."""
        if not price_str or price_str.strip() == '' or price_str == '-':
            return None
        
        # Remove currency symbols and spaces
        cleaned = price_str.replace('$', '').replace(' ', '').replace(',', '.')
        
        # Extract first number if range (e.g., "DCA bis 84.000$" -> 84000)
        match = re.search(r'[\d.]+', cleaned)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None
    
    def _parse_exit_targets(self, exit_str: str) -> List[Dict[str, float]]:
        """Parse exit target string into list of ranges."""
        if not exit_str or exit_str.strip() == '' or exit_str == '-':
            return []
        
        targets = []
        # Match patterns like "1.) 124488.50$-132072.10$"
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
        """Determine which tier a coin belongs to based on context."""
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
        """Load portfolio from Notion CSV export."""
        try:
            with open(self.portfolio_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            current_tier = 'main'  # Default tier
            
            for row in rows:
                project = row.get('Project', '').strip()
                ticker = row.get('Ticker', '').strip()
                
                # Check if this is a tier header
                if project and not ticker:
                    current_tier = self._determine_tier(project, current_tier)
                    continue
                
                # Skip empty rows and non-prioritized coins
                if not ticker or current_tier == 'not_prioritized':
                    continue
                
                # Parse coin data
                coin_data = {
                    'name': project,
                    'symbol': ticker.upper(),
                    'allocation': row.get('Allocation', '').strip(),
                    'buy_target': self._parse_price(row.get('Buy target', '')),
                    'category': row.get('Category', '').strip(),
                    'notes': row.get('Notes', '').strip(),
                    'conservative_exits': self._parse_exit_targets(row.get('Conservative exits', '')),
                    'optimistic_exits': self._parse_exit_targets(row.get('Optimistic exits', '')),
                    'tier': current_tier
                }
                
                self.tiers[current_tier]['coins'].append(coin_data)
            
            return self.tiers
            
        except Exception as e:
            print(f"Error loading portfolio: {e}")
            return {}
    
    async def fetch_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Fetch current prices from CoinGecko."""
        # Map symbols to CoinGecko IDs (simplified mapping)
        symbol_to_id = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'DOT': 'polkadot',
            'RIO': 'realio-network',
            'INJ': 'injective-protocol',
            'TAO': 'bittensor',
            'VRA': 'verasity',
            'NMT': 'netmind-token',
            'RENDER': 'render-token',
            'IOTX': 'iotex',
            'LINK': 'chainlink',
            'HBAR': 'hedera-hashgraph',
            'LL': 'lightlink',
            'QUBIC': 'qubic-network',
            'ZEPH': 'zephyr-protocol',
            'BCH': 'bitcoin-cash',
            'KNDX': 'kondux',
            'VELO': 'velo',
            'ALPH': 'alephium',
            'KAS': 'kaspa',
            'HYPE': 'hyperliquid',
            'OCTA': 'octaspace',
            'XNA': 'neurai',
            'ONDO': 'ondo-finance',
            'VET': 'vechain',
            'DAG': 'constellation-labs'
        }
        
        # Get CoinGecko IDs for symbols
        ids = [symbol_to_id.get(s) for s in symbols if symbol_to_id.get(s)]
        
        if not ids:
            return {}
        
        try:
            url = 'https://api.coingecko.com/api/v3/simple/price'
            params = {
                'ids': ','.join(ids),
                'vs_currencies': 'usd'
            }
            
            headers = {}
            if self.coingecko_api_key:
                headers['x-cg-pro-api-key'] = self.coingecko_api_key
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Map back to symbols
                        prices = {}
                        for symbol, cg_id in symbol_to_id.items():
                            if cg_id in data:
                                prices[symbol] = data[cg_id]['usd']
                        
                        return prices
                    else:
                        print(f"CoinGecko API error: {response.status}")
                        return {}
                        
        except Exception as e:
            print(f"Error fetching prices: {e}")
            return {}
    
    def analyze_position(self, coin: Dict, current_price: float) -> Dict:
        """Analyze a coin position against targets."""
        analysis = {
            'symbol': coin['symbol'],
            'name': coin['name'],
            'tier': coin['tier'],
            'current_price': current_price,
            'buy_target': coin['buy_target'],
            'allocation': coin['allocation'],
            'category': coin['category'],
            'signals': []
        }
        
        # Check buy opportunity
        if coin['buy_target'] and current_price <= coin['buy_target']:
            distance = ((coin['buy_target'] - current_price) / coin['buy_target']) * 100
            analysis['signals'].append({
                'type': 'BUY',
                'message': f"Kaufgelegenheit! Preis {distance:.1f}% unter Kaufziel",
                'urgency': 'high' if distance > 10 else 'medium'
            })
        
        # Check conservative exit targets
        for target in coin['conservative_exits']:
            if current_price >= target['low']:
                if current_price <= target['high']:
                    analysis['signals'].append({
                        'type': 'CONSERVATIVE_EXIT',
                        'level': target['level'],
                        'message': f"Konservatives Ziel {target['level']} erreicht ({target['low']:.2f}$ - {target['high']:.2f}$)",
                        'urgency': 'medium'
                    })
                elif current_price > target['high']:
                    analysis['signals'].append({
                        'type': 'CONSERVATIVE_EXIT_EXCEEDED',
                        'level': target['level'],
                        'message': f"Konservatives Ziel {target['level']} überschritten!",
                        'urgency': 'high'
                    })
        
        # Check optimistic exit targets
        for target in coin['optimistic_exits']:
            if current_price >= target['low']:
                if current_price <= target['high']:
                    analysis['signals'].append({
                        'type': 'OPTIMISTIC_EXIT',
                        'level': target['level'],
                        'message': f"Optimistisches Ziel {target['level']} erreicht ({target['low']:.2f}$ - {target['high']:.2f}$)",
                        'urgency': 'high'
                    })
                elif current_price > target['high']:
                    analysis['signals'].append({
                        'type': 'OPTIMISTIC_EXIT_EXCEEDED',
                        'level': target['level'],
                        'message': f"Optimistisches Ziel {target['level']} überschritten! 🚀",
                        'urgency': 'critical'
                    })
        
        return analysis
    
    async def run(self) -> Dict:
        """Run portfolio tracking analysis."""
        print("=== Portfolio Tracker V2 (Notion Integration) ===")
        
        # Load portfolio
        tiers = self.load_portfolio()
        
        # Collect all symbols
        all_symbols = []
        for tier_data in tiers.values():
            all_symbols.extend([coin['symbol'] for coin in tier_data['coins']])
        
        print(f"Tracking {len(all_symbols)} coins across {len([t for t in tiers.values() if t['coins']])} tiers")
        
        # Fetch prices
        prices = await self.fetch_prices(all_symbols)
        print(f"Fetched prices for {len(prices)} coins")
        
        # Analyze positions
        results = {
            'timestamp': datetime.now().isoformat(),
            'tiers': {},
            'all_signals': [],
            'summary': {
                'total_coins': len(all_symbols),
                'prices_fetched': len(prices),
                'buy_opportunities': 0,
                'exit_signals': 0
            }
        }
        
        for tier_key, tier_data in tiers.items():
            if not tier_data['coins']:
                continue
            
            tier_results = {
                'name': tier_data['name'],
                'emoji': tier_data['emoji'],
                'coins': []
            }
            
            for coin in tier_data['coins']:
                current_price = prices.get(coin['symbol'])
                
                if current_price:
                    analysis = self.analyze_position(coin, current_price)
                    tier_results['coins'].append(analysis)
                    
                    # Count signals
                    for signal in analysis['signals']:
                        if signal['type'] == 'BUY':
                            results['summary']['buy_opportunities'] += 1
                        elif 'EXIT' in signal['type']:
                            results['summary']['exit_signals'] += 1
                        
                        results['all_signals'].append({
                            **signal,
                            'coin': coin['name'],
                            'symbol': coin['symbol'],
                            'tier': tier_data['name']
                        })
            
            results['tiers'][tier_key] = tier_results
        
        return results

