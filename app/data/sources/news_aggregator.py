"""
News aggregation and sentiment analysis from crypto news sources
"""
import aiohttp
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from app.utils.logger import log
from app.config import get_settings

settings = get_settings()


class NewsAggregator:
    """Crypto news aggregator with sentiment analysis"""
    
    # CryptoPanic API (Free tier: 20 calls/day, no auth needed for public feed)
    CRYPTOPANIC_URL = "https://cryptopanic.com/api/v1/posts/"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'cryptopanic_api_key', 'free')
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_news(
        self,
        symbol: Optional[str] = None,
        limit: int = 20,
        filter_type: str = "hot"
    ) -> Optional[List[Dict]]:
        """
        Get crypto news from CryptoPanic
        
        Args:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')
            limit: Number of news items to fetch
            filter_type: 'hot', 'rising', 'bullish', 'bearish', 'important', 'saved', 'lol'
        
        Returns:
            List of news items with sentiment
        """
        try:
            session = await self._get_session()
            
            params = {
                'auth_token': self.api_key if self.api_key != 'free' else None,
                'public': 'true' if self.api_key == 'free' else None,
                'filter': filter_type,
            }
            
            # Add currency filter if specified
            if symbol:
                # Map common symbols to CryptoPanic currencies
                currency_map = {
                    'BTC': 'BTC',
                    'ETH': 'ETH',
                    'USDT': 'USDT',
                    'BNB': 'BNB',
                    'SOL': 'SOL',
                    'XRP': 'XRP',
                    'ADA': 'ADA',
                    'DOGE': 'DOGE',
                }
                
                # Extract base currency from symbol (e.g., BTC from BTC/USDT)
                base_currency = symbol.split('/')[0] if '/' in symbol else symbol
                currency = currency_map.get(base_currency.upper())
                
                if currency:
                    params['currencies'] = currency
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            async with session.get(self.CRYPTOPANIC_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'results' in data:
                        news_items = []
                        for item in data['results'][:limit]:
                            news_items.append(self._parse_news_item(item))
                        
                        log.info(f"Fetched {len(news_items)} news items for {symbol or 'all'}")
                        return news_items
                    else:
                        log.warning("No results in CryptoPanic response")
                        return []
                else:
                    log.warning(f"CryptoPanic API error: {response.status}")
                    return []
                    
        except Exception as e:
            log.error(f"Error fetching news: {e}")
            return []
    
    def _parse_news_item(self, item: Dict) -> Dict:
        """Parse news item from CryptoPanic"""
        # Extract sentiment from votes
        votes = item.get('votes', {})
        positive = votes.get('positive', 0)
        negative = votes.get('negative', 0)
        important = votes.get('important', 0)
        
        # Calculate sentiment score (-1 to +1)
        total_votes = positive + negative
        if total_votes > 0:
            sentiment_score = (positive - negative) / total_votes
        else:
            sentiment_score = 0.0
        
        # Classify sentiment
        if sentiment_score > 0.3:
            sentiment = "bullish"
        elif sentiment_score < -0.3:
            sentiment = "bearish"
        else:
            sentiment = "neutral"
        
        # Detect breaking news
        is_breaking = important > 5 or item.get('kind') == 'news'
        
        return {
            'id': item.get('id'),
            'title': item.get('title'),
            'published_at': item.get('published_at'),
            'url': item.get('url'),
            'source': item.get('source', {}).get('title', 'Unknown'),
            'currencies': [c.get('code') for c in item.get('currencies', [])],
            'sentiment': sentiment,
            'sentiment_score': sentiment_score,
            'votes': {
                'positive': positive,
                'negative': negative,
                'important': important
            },
            'is_breaking': is_breaking
        }
    
    async def get_sentiment_summary(
        self,
        symbol: Optional[str] = None,
        hours: int = 24
    ) -> Optional[Dict]:
        """
        Get aggregated news sentiment for a symbol
        
        Returns:
            Dict with sentiment metrics
        """
        try:
            news_items = await self.get_news(symbol=symbol, limit=50)
            
            if not news_items:
                return None
            
            # Filter by time window
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            recent_news = [
                item for item in news_items
                if datetime.fromisoformat(item['published_at'].replace('Z', '+00:00')) > cutoff_time
            ]
            
            if not recent_news:
                return None
            
            # Calculate aggregate metrics
            total_items = len(recent_news)
            bullish_count = sum(1 for item in recent_news if item['sentiment'] == 'bullish')
            bearish_count = sum(1 for item in recent_news if item['sentiment'] == 'bearish')
            neutral_count = total_items - bullish_count - bearish_count
            
            avg_sentiment = sum(item['sentiment_score'] for item in recent_news) / total_items
            
            breaking_news = [item for item in recent_news if item['is_breaking']]
            
            # Overall classification
            if avg_sentiment > 0.2:
                overall_sentiment = "bullish"
            elif avg_sentiment < -0.2:
                overall_sentiment = "bearish"
            else:
                overall_sentiment = "neutral"
            
            return {
                'symbol': symbol,
                'time_window_hours': hours,
                'total_news': total_items,
                'sentiment_breakdown': {
                    'bullish': bullish_count,
                    'bearish': bearish_count,
                    'neutral': neutral_count
                },
                'sentiment_score': avg_sentiment,
                'overall_sentiment': overall_sentiment,
                'breaking_news_count': len(breaking_news),
                'breaking_news': breaking_news[:3],  # Top 3 breaking news
                'recent_headlines': [
                    {
                        'title': item['title'],
                        'sentiment': item['sentiment'],
                        'source': item['source']
                    }
                    for item in recent_news[:5]
                ],
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            log.error(f"Error calculating sentiment summary: {e}")
            return None
    
    def interpret_news_sentiment(self, sentiment_data: Dict) -> Dict:
        """
        Interpret news sentiment for trading decisions
        
        Returns:
            Trading signal interpretation
        """
        if not sentiment_data:
            return {
                'signal': 'neutral',
                'confidence': 0.0,
                'reason': 'No news data available'
            }
        
        score = sentiment_data['sentiment_score']
        breaking_count = sentiment_data['breaking_news_count']
        
        # High impact if breaking news
        impact_multiplier = 1.0 + (breaking_count * 0.1)
        
        if score > 0.3:
            return {
                'signal': 'bullish',
                'confidence': min(abs(score) * impact_multiplier, 1.0),
                'reason': f"Positive news sentiment ({sentiment_data['sentiment_breakdown']['bullish']} bullish articles)"
            }
        elif score < -0.3:
            return {
                'signal': 'bearish',
                'confidence': min(abs(score) * impact_multiplier, 1.0),
                'reason': f"Negative news sentiment ({sentiment_data['sentiment_breakdown']['bearish']} bearish articles)"
            }
        else:
            return {
                'signal': 'neutral',
                'confidence': 0.3,
                'reason': 'Neutral news sentiment'
            }
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

