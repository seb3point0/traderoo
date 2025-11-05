"""
Sentiment analysis integration for market sentiment
"""
import aiohttp
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from app.utils.logger import log


class SentimentAnalyzer:
    """Sentiment analysis client"""
    
    # Using free Alternative.me Crypto Fear & Greed Index
    FEAR_GREED_URL = "https://api.alternative.me/fng/"
    
    def __init__(self):
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
    
    async def get_fear_greed_index(self, limit: int = 1) -> Optional[Dict]:
        """
        Get Crypto Fear & Greed Index
        
        Returns:
            Dict with 'value' (0-100), 'value_classification' (e.g., 'Extreme Fear')
        """
        try:
            session = await self._get_session()
            params = {'limit': limit}
            
            async with session.get(self.FEAR_GREED_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    log.warning(f"Fear & Greed API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching Fear & Greed Index: {e}")
            return None
    
    async def get_sentiment_score(self) -> Optional[float]:
        """
        Get normalized sentiment score (0-100)
        
        Returns:
            Float between 0 (extreme fear) and 100 (extreme greed)
        """
        try:
            data = await self.get_fear_greed_index(limit=1)
            if data and 'data' in data and len(data['data']) > 0:
                return float(data['data'][0]['value'])
            return None
        except Exception as e:
            log.error(f"Error parsing sentiment score: {e}")
            return None
    
    async def get_sentiment_classification(self) -> Optional[str]:
        """
        Get sentiment classification
        
        Returns:
            String like 'Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed'
        """
        try:
            data = await self.get_fear_greed_index(limit=1)
            if data and 'data' in data and len(data['data']) > 0:
                return data['data'][0]['value_classification']
            return None
        except Exception as e:
            log.error(f"Error parsing sentiment classification: {e}")
            return None
    
    async def get_sentiment_trend(self, days: int = 7) -> Optional[Dict]:
        """
        Get sentiment trend over time
        
        Returns:
            Dict with 'current', 'average', 'trend' ('increasing'/'decreasing')
        """
        try:
            data = await self.get_fear_greed_index(limit=days)
            if not data or 'data' not in data:
                return None
            
            values = [float(item['value']) for item in data['data']]
            
            if len(values) < 2:
                return None
            
            current = values[0]
            average = sum(values) / len(values)
            trend = "increasing" if current > average else "decreasing"
            
            return {
                'current': current,
                'average': average,
                'trend': trend,
                'historical_values': values
            }
        except Exception as e:
            log.error(f"Error calculating sentiment trend: {e}")
            return None
    
    def interpret_sentiment(self, score: float) -> Dict:
        """
        Interpret sentiment score for trading decisions
        
        Args:
            score: Sentiment score (0-100)
        
        Returns:
            Dict with trading signal and confidence
        """
        if score <= 20:
            return {
                'signal': 'strong_buy',
                'reason': 'Extreme fear - potential buying opportunity',
                'confidence': 0.8
            }
        elif score <= 40:
            return {
                'signal': 'buy',
                'reason': 'Fear - cautious buying opportunity',
                'confidence': 0.6
            }
        elif score <= 60:
            return {
                'signal': 'neutral',
                'reason': 'Neutral market sentiment',
                'confidence': 0.3
            }
        elif score <= 80:
            return {
                'signal': 'sell',
                'reason': 'Greed - consider taking profits',
                'confidence': 0.6
            }
        else:
            return {
                'signal': 'strong_sell',
                'reason': 'Extreme greed - high risk of correction',
                'confidence': 0.8
            }
    
    async def get_comprehensive_sentiment(self) -> Optional[Dict]:
        """Get comprehensive sentiment analysis"""
        try:
            score = await self.get_sentiment_score()
            classification = await self.get_sentiment_classification()
            trend = await self.get_sentiment_trend(days=7)
            
            if score is None:
                return None
            
            interpretation = self.interpret_sentiment(score)
            
            return {
                'score': score,
                'classification': classification,
                'trend': trend,
                'trading_signal': interpretation,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            log.error(f"Error getting comprehensive sentiment: {e}")
            return None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

