"""
Social sentiment tracking from Twitter, Reddit, and other platforms
"""
import aiohttp
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from app.utils.logger import log
from app.config import get_settings

settings = get_settings()


class SocialSentimentTracker:
    """Social media sentiment tracker for crypto"""
    
    # Using free CoinGecko API for social metrics
    COINGECKO_URL = "https://api.coingecko.com/api/v3"
    
    # Mapping common symbols to CoinGecko IDs
    SYMBOL_TO_ID = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'USDT': 'tether',
        'BNB': 'binancecoin',
        'SOL': 'solana',
        'XRP': 'ripple',
        'ADA': 'cardano',
        'DOGE': 'dogecoin',
        'AVAX': 'avalanche-2',
        'DOT': 'polkadot',
        'MATIC': 'matic-network',
        'LINK': 'chainlink',
        'UNI': 'uniswap',
        'ATOM': 'cosmos',
        'LTC': 'litecoin'
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'lunarcrush_api_key', None)
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
    
    def _get_coingecko_id(self, symbol: str) -> Optional[str]:
        """Map trading symbol to CoinGecko ID"""
        # Extract base currency from symbol (e.g., BTC from BTC/USDT)
        base_currency = symbol.split('/')[0] if '/' in symbol else symbol
        return self.SYMBOL_TO_ID.get(base_currency.upper())
    
    async def get_social_metrics(self, symbol: str) -> Optional[Dict]:
        """
        Get social media metrics from CoinGecko
        
        Returns:
            Dict with social metrics including Twitter, Reddit, etc.
        """
        try:
            coin_id = self._get_coingecko_id(symbol)
            if not coin_id:
                log.warning(f"No CoinGecko ID mapping for {symbol}")
                return None
            
            session = await self._get_session()
            url = f"{self.COINGECKO_URL}/coins/{coin_id}"
            
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'false',
                'community_data': 'true',
                'developer_data': 'false'
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_social_metrics(data, symbol)
                elif response.status == 429:
                    log.warning("CoinGecko rate limit hit")
                    return None
                else:
                    log.warning(f"CoinGecko API error: {response.status}")
                    return None
                    
        except Exception as e:
            log.error(f"Error fetching social metrics: {e}")
            return None
    
    def _parse_social_metrics(self, data: Dict, symbol: str) -> Dict:
        """Parse social metrics from CoinGecko response"""
        community_data = data.get('community_data', {})
        
        # Twitter metrics
        twitter_followers = community_data.get('twitter_followers', 0)
        
        # Reddit metrics
        reddit_subscribers = community_data.get('reddit_subscribers', 0)
        reddit_active_users = community_data.get('reddit_accounts_active_48h', 0)
        reddit_posts_48h = community_data.get('reddit_posts_48h', 0)
        reddit_comments_48h = community_data.get('reddit_comments_48h', 0)
        
        # Telegram
        telegram_users = community_data.get('telegram_channel_user_count', 0)
        
        # Calculate engagement scores
        reddit_engagement = reddit_active_users + reddit_posts_48h + reddit_comments_48h
        
        # Overall social score (normalized)
        # Higher values indicate more social activity
        social_score = (
            (twitter_followers / 1000000) * 0.3 +  # Twitter weight
            (reddit_subscribers / 100000) * 0.3 +   # Reddit weight
            (reddit_engagement / 1000) * 0.4        # Engagement weight
        )
        
        # Sentiment estimation based on engagement vs followers ratio
        if reddit_subscribers > 0:
            engagement_ratio = reddit_engagement / reddit_subscribers
            
            # High engagement ratio suggests bullish sentiment
            if engagement_ratio > 0.05:
                sentiment = "bullish"
                sentiment_score = min(engagement_ratio * 10, 1.0)
            elif engagement_ratio < 0.01:
                sentiment = "bearish"
                sentiment_score = -min(0.01 / engagement_ratio, 1.0) if engagement_ratio > 0 else -0.5
            else:
                sentiment = "neutral"
                sentiment_score = 0.0
        else:
            sentiment = "neutral"
            sentiment_score = 0.0
        
        return {
            'symbol': symbol,
            'twitter': {
                'followers': twitter_followers
            },
            'reddit': {
                'subscribers': reddit_subscribers,
                'active_users_48h': reddit_active_users,
                'posts_48h': reddit_posts_48h,
                'comments_48h': reddit_comments_48h,
                'engagement_score': reddit_engagement
            },
            'telegram': {
                'users': telegram_users
            },
            'social_score': social_score,
            'sentiment': sentiment,
            'sentiment_score': sentiment_score,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def get_trending_coins(self) -> Optional[List[Dict]]:
        """Get trending coins from CoinGecko"""
        try:
            session = await self._get_session()
            url = f"{self.COINGECKO_URL}/search/trending"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    trending = []
                    for item in data.get('coins', [])[:10]:
                        coin = item.get('item', {})
                        trending.append({
                            'symbol': coin.get('symbol', '').upper(),
                            'name': coin.get('name'),
                            'market_cap_rank': coin.get('market_cap_rank'),
                            'score': coin.get('score', 0)
                        })
                    
                    return trending
                else:
                    log.warning(f"CoinGecko trending API error: {response.status}")
                    return None
                    
        except Exception as e:
            log.error(f"Error fetching trending coins: {e}")
            return None
    
    async def get_sentiment_summary(self, symbol: str) -> Optional[Dict]:
        """Get comprehensive social sentiment summary"""
        try:
            metrics = await self.get_social_metrics(symbol)
            
            if not metrics:
                return None
            
            # Determine overall sentiment strength
            social_score = metrics['social_score']
            sentiment = metrics['sentiment']
            sentiment_score = metrics['sentiment_score']
            
            # Calculate confidence based on data availability
            confidence = 0.0
            if metrics['reddit']['subscribers'] > 10000:
                confidence += 0.4
            if metrics['reddit']['engagement_score'] > 100:
                confidence += 0.3
            if metrics['twitter']['followers'] > 50000:
                confidence += 0.3
            
            # Interpret for trading
            if sentiment == 'bullish' and social_score > 2.0:
                signal = 'buy'
                reason = 'Strong social engagement and positive sentiment'
            elif sentiment == 'bearish' or social_score < 0.5:
                signal = 'sell'
                reason = 'Weak social interest or negative sentiment'
            else:
                signal = 'neutral'
                reason = 'Neutral social sentiment'
            
            return {
                'symbol': symbol,
                'sentiment': sentiment,
                'sentiment_score': sentiment_score,
                'social_score': social_score,
                'confidence': confidence,
                'trading_signal': {
                    'signal': signal,
                    'confidence': confidence,
                    'reason': reason
                },
                'metrics': metrics,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            log.error(f"Error getting sentiment summary: {e}")
            return None
    
    def interpret_social_sentiment(self, sentiment_data: Dict) -> Dict:
        """
        Interpret social sentiment for trading decisions
        
        Returns:
            Trading signal interpretation
        """
        if not sentiment_data:
            return {
                'signal': 'neutral',
                'confidence': 0.0,
                'reason': 'No social data available'
            }
        
        return sentiment_data.get('trading_signal', {
            'signal': 'neutral',
            'confidence': 0.0,
            'reason': 'Unable to interpret social sentiment'
        })
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

