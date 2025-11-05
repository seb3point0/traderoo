"""
Comprehensive data aggregator combining all data sources
"""
import asyncio
from typing import Optional, Dict
from datetime import datetime
import pandas as pd

from app.data.sources.sentiment import SentimentAnalyzer
from app.data.sources.news_aggregator import NewsAggregator
from app.data.sources.social_sentiment import SocialSentimentTracker
from app.data.sources.onchain_metrics import OnChainMetricsTracker
from app.utils.logger import log


class DataAggregator:
    """
    Aggregates data from multiple sources for comprehensive market analysis
    """
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.news_aggregator = NewsAggregator()
        self.social_tracker = SocialSentimentTracker()
        self.onchain_tracker = OnChainMetricsTracker()
    
    async def get_comprehensive_data(
        self,
        symbol: str,
        df: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Get comprehensive market data from all sources
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            df: Optional DataFrame with OHLCV and indicators
        
        Returns:
            Dict with all market data and high-impact flag
        """
        try:
            # Gather data from all sources concurrently
            tasks = [
                self._get_technical_data(df),
                self._get_sentiment_data(),
                self._get_news_data(symbol),
                self._get_social_data(symbol),
                self._get_onchain_data(symbol)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            technical_data = results[0] if not isinstance(results[0], Exception) else {}
            sentiment_data = results[1] if not isinstance(results[1], Exception) else {}
            news_data = results[2] if not isinstance(results[2], Exception) else {}
            social_data = results[3] if not isinstance(results[3], Exception) else {}
            onchain_data = results[4] if not isinstance(results[4], Exception) else {}
            
            # Detect high-impact events
            is_high_impact = self._detect_high_impact_event(
                news_data, social_data, onchain_data, df
            )
            
            comprehensive_data = {
                'symbol': symbol,
                'technical': technical_data,
                'sentiment': sentiment_data,
                'news': news_data,
                'social': social_data,
                'onchain': onchain_data,
                'is_high_impact': is_high_impact,
                'high_impact_reasons': self._get_high_impact_reasons(
                    news_data, social_data, onchain_data, df
                ),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            log.info(
                f"Aggregated data for {symbol} | "
                f"High Impact: {is_high_impact} | "
                f"Sources: {len([r for r in results if not isinstance(r, Exception)])}/5"
            )
            
            return comprehensive_data
            
        except Exception as e:
            log.error(f"Error aggregating comprehensive data: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'is_high_impact': False,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _get_technical_data(self, df: Optional[pd.DataFrame]) -> Dict:
        """Extract technical indicators from DataFrame"""
        if df is None or df.empty:
            return {}
        
        try:
            latest = df.iloc[-1]
            
            technical = {
                'price': float(latest.get('close', 0)),
                'volume': float(latest.get('volume', 0)),
            }
            
            # Add common indicators if available
            indicator_fields = [
                'rsi', 'macd', 'macd_signal', 'macd_hist',
                'bb_upper', 'bb_middle', 'bb_lower',
                'sma_50', 'sma_200', 'ema_12', 'ema_26',
                'atr', 'adx', 'stoch_k', 'stoch_d',
                'obv', 'vwap'
            ]
            
            for field in indicator_fields:
                if field in df.columns:
                    technical[field] = float(latest.get(field, 0))
            
            # Calculate price changes
            if len(df) >= 2:
                prev_close = df.iloc[-2]['close']
                technical['price_change_pct'] = ((technical['price'] - prev_close) / prev_close) * 100
            
            # Volume analysis
            if 'volume' in df.columns and len(df) >= 20:
                avg_volume = df['volume'].tail(20).mean()
                technical['volume_vs_avg'] = (technical['volume'] / avg_volume) if avg_volume > 0 else 1.0
            
            return technical
            
        except Exception as e:
            log.error(f"Error extracting technical data: {e}")
            return {}
    
    async def _get_sentiment_data(self) -> Dict:
        """Get market sentiment (Fear & Greed)"""
        try:
            sentiment = await self.sentiment_analyzer.get_comprehensive_sentiment()
            return sentiment or {}
        except Exception as e:
            log.error(f"Error getting sentiment data: {e}")
            return {}
    
    async def _get_news_data(self, symbol: str) -> Dict:
        """Get news sentiment"""
        try:
            news_summary = await self.news_aggregator.get_sentiment_summary(symbol, hours=24)
            return news_summary or {}
        except Exception as e:
            log.error(f"Error getting news data: {e}")
            return {}
    
    async def _get_social_data(self, symbol: str) -> Dict:
        """Get social sentiment"""
        try:
            social_summary = await self.social_tracker.get_sentiment_summary(symbol)
            return social_summary or {}
        except Exception as e:
            log.error(f"Error getting social data: {e}")
            return {}
    
    async def _get_onchain_data(self, symbol: str) -> Dict:
        """Get on-chain metrics"""
        try:
            onchain_metrics = await self.onchain_tracker.get_comprehensive_metrics(symbol)
            return onchain_metrics or {}
        except Exception as e:
            log.error(f"Error getting on-chain data: {e}")
            return {}
    
    def _detect_high_impact_event(
        self,
        news_data: Dict,
        social_data: Dict,
        onchain_data: Dict,
        df: Optional[pd.DataFrame]
    ) -> bool:
        """
        Detect high-impact events that require real-time AI analysis
        
        Returns:
            True if high-impact event detected
        """
        # 1. Breaking news
        if news_data.get('breaking_news_count', 0) > 0:
            return True
        
        # 2. Extreme news sentiment
        news_sentiment_score = news_data.get('sentiment_score', 0)
        if abs(news_sentiment_score) > 0.5:
            return True
        
        # 3. High whale activity
        onchain_metrics = onchain_data.get('metrics', {})
        if 'whale_activity' in onchain_metrics:
            whale_activity = onchain_metrics['whale_activity'].get('whale_activity', 'low')
            if whale_activity == 'high':
                return True
        
        # 4. Large price swing
        if df is not None and not df.empty and len(df) >= 2:
            latest_price = df.iloc[-1]['close']
            prev_price = df.iloc[-2]['close']
            price_change_pct = abs((latest_price - prev_price) / prev_price) * 100
            
            if price_change_pct > 5:  # >5% price move
                return True
        
        # 5. Extreme volume
        technical = {}
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            if 'volume' in df.columns and len(df) >= 20:
                current_volume = latest['volume']
                avg_volume = df['volume'].tail(20).mean()
                if current_volume > avg_volume * 2:  # 2x average volume
                    return True
        
        # 6. Extreme Fear & Greed
        # (covered in sentiment analysis)
        
        return False
    
    def _get_high_impact_reasons(
        self,
        news_data: Dict,
        social_data: Dict,
        onchain_data: Dict,
        df: Optional[pd.DataFrame]
    ) -> list:
        """Get list of reasons for high-impact classification"""
        reasons = []
        
        # Breaking news
        breaking_count = news_data.get('breaking_news_count', 0)
        if breaking_count > 0:
            reasons.append(f"Breaking news: {breaking_count} items")
        
        # Extreme sentiment
        news_sentiment = news_data.get('sentiment_score', 0)
        if news_sentiment > 0.5:
            reasons.append("Very positive news sentiment")
        elif news_sentiment < -0.5:
            reasons.append("Very negative news sentiment")
        
        # Whale activity
        onchain_metrics = onchain_data.get('metrics', {})
        if 'whale_activity' in onchain_metrics:
            whale_activity = onchain_metrics['whale_activity'].get('whale_activity', 'low')
            if whale_activity == 'high':
                reasons.append("High whale activity detected")
        
        # Price swing
        if df is not None and not df.empty and len(df) >= 2:
            latest_price = df.iloc[-1]['close']
            prev_price = df.iloc[-2]['close']
            price_change_pct = ((latest_price - prev_price) / prev_price) * 100
            
            if abs(price_change_pct) > 5:
                direction = "up" if price_change_pct > 0 else "down"
                reasons.append(f"Large price move: {abs(price_change_pct):.1f}% {direction}")
        
        # High volume
        if df is not None and not df.empty and 'volume' in df.columns and len(df) >= 20:
            current_volume = df.iloc[-1]['volume']
            avg_volume = df['volume'].tail(20).mean()
            if current_volume > avg_volume * 2:
                multiplier = current_volume / avg_volume
                reasons.append(f"High volume: {multiplier:.1f}x average")
        
        return reasons
    
    def get_aggregated_sentiment(self, comprehensive_data: Dict) -> Dict:
        """
        Calculate aggregated sentiment across all sources
        
        Returns:
            Dict with overall sentiment and confidence
        """
        sentiments = []
        weights = []
        
        # Technical sentiment (if price trending)
        technical = comprehensive_data.get('technical', {})
        if 'price_change_pct' in technical:
            price_change = technical['price_change_pct']
            if abs(price_change) > 2:
                sentiments.append(1.0 if price_change > 0 else -1.0)
                weights.append(0.3)
        
        # Fear & Greed sentiment
        sentiment_data = comprehensive_data.get('sentiment', {})
        if 'score' in sentiment_data:
            fg_score = sentiment_data['score']
            # Normalize 0-100 to -1 to 1
            fg_normalized = (fg_score - 50) / 50
            sentiments.append(fg_normalized)
            weights.append(0.25)
        
        # News sentiment
        news_data = comprehensive_data.get('news', {})
        if 'sentiment_score' in news_data:
            sentiments.append(news_data['sentiment_score'])
            weights.append(0.25)
        
        # Social sentiment
        social_data = comprehensive_data.get('social', {})
        if 'sentiment_score' in social_data:
            sentiments.append(social_data['sentiment_score'])
            weights.append(0.1)
        
        # On-chain sentiment
        onchain_data = comprehensive_data.get('onchain', {})
        if 'overall_sentiment' in onchain_data:
            onchain_sentiment = onchain_data['overall_sentiment']
            sentiment_map = {'bullish': 0.5, 'neutral': 0.0, 'bearish': -0.5}
            sentiments.append(sentiment_map.get(onchain_sentiment, 0.0))
            weights.append(0.1)
        
        # Calculate weighted average
        if sentiments and weights:
            total_weight = sum(weights)
            weighted_sentiment = sum(s * w for s, w in zip(sentiments, weights)) / total_weight
            
            # Classify
            if weighted_sentiment > 0.2:
                classification = "bullish"
            elif weighted_sentiment < -0.2:
                classification = "bearish"
            else:
                classification = "neutral"
            
            # Calculate confidence based on data availability
            confidence = min(len(sentiments) / 5, 1.0)  # Max confidence if all 5 sources
            
            return {
                'aggregated_sentiment_score': weighted_sentiment,
                'classification': classification,
                'confidence': confidence,
                'sources_used': len(sentiments)
            }
        
        return {
            'aggregated_sentiment_score': 0.0,
            'classification': 'neutral',
            'confidence': 0.0,
            'sources_used': 0
        }
    
    async def close(self):
        """Close all data source sessions"""
        await self.sentiment_analyzer.close()
        await self.news_aggregator.close()
        await self.social_tracker.close()
        await self.onchain_tracker.close()

