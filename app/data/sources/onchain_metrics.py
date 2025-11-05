"""
On-chain metrics tracking using free blockchain APIs
"""
import aiohttp
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from app.utils.logger import log
from app.config import get_settings

settings = get_settings()


class OnChainMetricsTracker:
    """On-chain metrics tracker using free APIs"""
    
    # Free blockchain.com API
    BLOCKCHAIN_COM_URL = "https://blockchain.info"
    
    # CoinGecko for additional market data
    COINGECKO_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'glassnode_api_key', None)
        self.session: Optional[aiohttp.ClientSession] = None
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes cache
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_btc_network_stats(self) -> Optional[Dict]:
        """Get Bitcoin network statistics"""
        try:
            # Check cache
            cache_key = 'btc_network_stats'
            if cache_key in self._cache:
                cached_data, cached_time = self._cache[cache_key]
                if (datetime.utcnow() - cached_time).total_seconds() < self._cache_ttl:
                    return cached_data
            
            session = await self._get_session()
            url = f"{self.BLOCKCHAIN_COM_URL}/stats"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    stats = {
                        'network': 'bitcoin',
                        'market_price_usd': data.get('market_price_usd'),
                        'hash_rate': data.get('hash_rate'),
                        'total_fees_btc': data.get('total_fees_btc'),
                        'n_btc_mined': data.get('n_btc_mined'),
                        'n_tx': data.get('n_tx'),
                        'n_blocks_mined': data.get('n_blocks_mined'),
                        'minutes_between_blocks': data.get('minutes_between_blocks'),
                        'difficulty': data.get('difficulty'),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    # Cache the result
                    self._cache[cache_key] = (stats, datetime.utcnow())
                    
                    return stats
                else:
                    log.warning(f"Blockchain.com API error: {response.status}")
                    return None
                    
        except Exception as e:
            log.error(f"Error fetching BTC network stats: {e}")
            return None
    
    async def get_exchange_flows(self, symbol: str) -> Optional[Dict]:
        """
        Estimate exchange flows using CoinGecko market data
        
        Note: True exchange flow data requires paid APIs like Glassnode
        This provides a proxy using volume changes
        """
        try:
            # Map symbol to CoinGecko ID
            symbol_map = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'BNB': 'binancecoin',
                'SOL': 'solana'
            }
            
            base_currency = symbol.split('/')[0] if '/' in symbol else symbol
            coin_id = symbol_map.get(base_currency.upper())
            
            if not coin_id:
                return None
            
            session = await self._get_session()
            url = f"{self.COINGECKO_URL}/coins/{coin_id}/market_chart"
            
            params = {
                'vs_currency': 'usd',
                'days': '7',
                'interval': 'daily'
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Analyze volume trends as proxy for exchange flows
                    volumes = data.get('total_volumes', [])
                    
                    if len(volumes) < 2:
                        return None
                    
                    # Calculate volume trend
                    recent_volume = sum(v[1] for v in volumes[-3:]) / 3  # Last 3 days avg
                    older_volume = sum(v[1] for v in volumes[-7:-3]) / 4  # Previous 4 days avg
                    
                    volume_change = ((recent_volume - older_volume) / older_volume * 100) if older_volume > 0 else 0
                    
                    # Estimate flow direction
                    # Increasing volume often correlates with exchange inflows (selling pressure)
                    # Decreasing volume suggests outflows (accumulation)
                    if volume_change > 20:
                        flow_direction = 'inflow'
                        sentiment = 'bearish'
                        confidence = 0.6
                    elif volume_change < -20:
                        flow_direction = 'outflow'
                        sentiment = 'bullish'
                        confidence = 0.6
                    else:
                        flow_direction = 'neutral'
                        sentiment = 'neutral'
                        confidence = 0.3
                    
                    return {
                        'symbol': symbol,
                        'flow_direction': flow_direction,
                        'volume_change_pct': volume_change,
                        'recent_volume_usd': recent_volume,
                        'sentiment': sentiment,
                        'confidence': confidence,
                        'note': 'Proxy metric based on volume trends',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                else:
                    log.warning(f"CoinGecko API error: {response.status}")
                    return None
                    
        except Exception as e:
            log.error(f"Error estimating exchange flows: {e}")
            return None
    
    async def get_large_transactions(self, symbol: str, min_value_usd: float = 1000000) -> Optional[Dict]:
        """
        Get large transaction alerts (whale activity)
        
        Note: Only available for BTC with free APIs
        For other chains, requires paid services
        """
        try:
            if not symbol.startswith('BTC'):
                return {
                    'symbol': symbol,
                    'large_transactions': [],
                    'whale_activity': 'unavailable',
                    'note': 'Large transaction tracking only available for BTC with free APIs'
                }
            
            # For BTC, we can use blockchain.com
            session = await self._get_session()
            url = f"{self.BLOCKCHAIN_COM_URL}/unconfirmed-transactions"
            
            params = {
                'format': 'json'
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Get current BTC price
                    btc_price = await self._get_btc_price()
                    if not btc_price:
                        return None
                    
                    # Filter large transactions
                    large_txs = []
                    for tx in data.get('txs', [])[:50]:  # Check recent 50 txs
                        value_btc = sum(out.get('value', 0) for out in tx.get('out', [])) / 100000000
                        value_usd = value_btc * btc_price
                        
                        if value_usd >= min_value_usd:
                            large_txs.append({
                                'hash': tx.get('hash'),
                                'value_btc': value_btc,
                                'value_usd': value_usd,
                                'time': tx.get('time'),
                                'size': tx.get('size')
                            })
                    
                    # Whale activity analysis
                    if len(large_txs) > 5:
                        whale_activity = 'high'
                        sentiment = 'volatile'
                    elif len(large_txs) > 2:
                        whale_activity = 'moderate'
                        sentiment = 'neutral'
                    else:
                        whale_activity = 'low'
                        sentiment = 'stable'
                    
                    return {
                        'symbol': symbol,
                        'large_transactions': large_txs[:10],  # Top 10
                        'whale_activity': whale_activity,
                        'total_large_txs': len(large_txs),
                        'sentiment': sentiment,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                else:
                    log.warning(f"Blockchain.com API error: {response.status}")
                    return None
                    
        except Exception as e:
            log.error(f"Error fetching large transactions: {e}")
            return None
    
    async def _get_btc_price(self) -> Optional[float]:
        """Get current BTC price"""
        try:
            session = await self._get_session()
            url = f"{self.COINGECKO_URL}/simple/price"
            
            params = {
                'ids': 'bitcoin',
                'vs_currencies': 'usd'
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('bitcoin', {}).get('usd')
                return None
                
        except Exception as e:
            log.error(f"Error fetching BTC price: {e}")
            return None
    
    async def get_comprehensive_metrics(self, symbol: str) -> Optional[Dict]:
        """Get comprehensive on-chain metrics"""
        try:
            metrics = {}
            
            # BTC-specific metrics
            if symbol.startswith('BTC'):
                network_stats = await self.get_btc_network_stats()
                if network_stats:
                    metrics['network_stats'] = network_stats
                
                large_txs = await self.get_large_transactions(symbol)
                if large_txs:
                    metrics['whale_activity'] = large_txs
            
            # Exchange flow proxy for all symbols
            exchange_flows = await self.get_exchange_flows(symbol)
            if exchange_flows:
                metrics['exchange_flows'] = exchange_flows
            
            if not metrics:
                return None
            
            # Overall on-chain sentiment
            sentiments = []
            if 'whale_activity' in metrics:
                whale_sentiment = metrics['whale_activity'].get('sentiment', 'neutral')
                sentiments.append(whale_sentiment)
            
            if 'exchange_flows' in metrics:
                flow_sentiment = metrics['exchange_flows'].get('sentiment', 'neutral')
                sentiments.append(flow_sentiment)
            
            # Aggregate sentiment
            if 'bearish' in sentiments:
                overall_sentiment = 'bearish'
            elif 'bullish' in sentiments:
                overall_sentiment = 'bullish'
            else:
                overall_sentiment = 'neutral'
            
            return {
                'symbol': symbol,
                'metrics': metrics,
                'overall_sentiment': overall_sentiment,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            log.error(f"Error getting comprehensive metrics: {e}")
            return None
    
    def interpret_onchain_metrics(self, metrics_data: Dict) -> Dict:
        """
        Interpret on-chain metrics for trading decisions
        
        Returns:
            Trading signal interpretation
        """
        if not metrics_data:
            return {
                'signal': 'neutral',
                'confidence': 0.0,
                'reason': 'No on-chain data available'
            }
        
        sentiment = metrics_data.get('overall_sentiment', 'neutral')
        
        # Calculate confidence based on data availability
        confidence = 0.3  # Base confidence
        if 'whale_activity' in metrics_data.get('metrics', {}):
            confidence += 0.2
        if 'exchange_flows' in metrics_data.get('metrics', {}):
            confidence += 0.2
        
        if sentiment == 'bullish':
            return {
                'signal': 'buy',
                'confidence': confidence,
                'reason': 'Bullish on-chain indicators'
            }
        elif sentiment == 'bearish':
            return {
                'signal': 'sell',
                'confidence': confidence,
                'reason': 'Bearish on-chain indicators'
            }
        else:
            return {
                'signal': 'neutral',
                'confidence': 0.2,
                'reason': 'Neutral on-chain activity'
            }
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

