"""
AI Market Analyzer with hybrid real-time/cached decision logic
"""
import json
from typing import Optional, Dict
from datetime import datetime
import pandas as pd

from ai.llm_client import LLMClient, LLMProvider
from ai.data_aggregator import DataAggregator
from ai.prompts import get_signal_validation_prompt, get_market_analysis_prompt
from app.core.cache_manager import get_cache_manager
from app.strategies.base import Signal
from app.utils.logger import log
from app.config import get_settings

settings = get_settings()


class AIMarketAnalyzer:
    """
    AI-powered market analyzer with hybrid caching strategy
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider = LLMProvider.OPENAI,
        enable_cache: bool = True
    ):
        self.llm_client = LLMClient(provider=llm_provider)
        self.data_aggregator = DataAggregator()
        self.enable_cache = enable_cache
        self.cache_manager = None
        
        # Configuration
        self.min_confidence = getattr(settings, 'ai_confidence_threshold', 60)
        self.cache_ttl = getattr(settings, 'ai_cache_ttl', 14400)  # 4 hours
    
    async def initialize(self):
        """Initialize cache manager"""
        if self.enable_cache:
            self.cache_manager = await get_cache_manager()
    
    async def validate_signal(
        self,
        strategy_name: str,
        signal: Signal,
        symbol: str,
        df: pd.DataFrame,
        entry_price: Optional[float] = None,
        force_realtime: bool = False
    ) -> Dict:
        """
        Validate a trading signal using AI analysis
        
        Args:
            strategy_name: Name of strategy generating signal
            signal: Trading signal
            symbol: Trading symbol
            df: DataFrame with OHLCV and indicators
            entry_price: Suggested entry price
            force_realtime: Force real-time analysis (skip cache)
        
        Returns:
            Dict with validation results
        """
        try:
            # Get comprehensive market data
            comprehensive_data = await self.data_aggregator.get_comprehensive_data(
                symbol=symbol,
                df=df
            )
            
            # Determine if we should use cache or go real-time
            is_high_impact = comprehensive_data.get('is_high_impact', False)
            use_realtime = force_realtime or is_high_impact
            
            if use_realtime:
                log.info(f"Using REAL-TIME AI analysis for {symbol}")
                reasons = comprehensive_data.get('high_impact_reasons', [])
                if reasons:
                    log.info(f"High-impact reasons: {', '.join(reasons)}")
                
                validation = await self._realtime_validation(
                    strategy_name,
                    signal,
                    symbol,
                    comprehensive_data,
                    entry_price
                )
            else:
                log.info(f"Using CACHED AI analysis for {symbol}")
                validation = await self._cached_validation(
                    strategy_name,
                    signal,
                    symbol,
                    comprehensive_data,
                    entry_price
                )
            
            # Add metadata
            validation['analysis_mode'] = 'realtime' if use_realtime else 'cached'
            validation['is_high_impact'] = is_high_impact
            validation['high_impact_reasons'] = comprehensive_data.get('high_impact_reasons', [])
            validation['timestamp'] = datetime.utcnow().isoformat()
            
            return validation
            
        except Exception as e:
            log.error(f"Error in AI signal validation: {e}")
            return self._default_validation(f"Error: {str(e)}")
    
    async def _realtime_validation(
        self,
        strategy_name: str,
        signal: Signal,
        symbol: str,
        comprehensive_data: Dict,
        entry_price: Optional[float]
    ) -> Dict:
        """Perform real-time AI validation"""
        try:
            # Generate prompt
            prompt = get_signal_validation_prompt(
                strategy_name=strategy_name,
                signal=signal,
                symbol=symbol,
                technical_data=comprehensive_data.get('technical', {}),
                sentiment_data=comprehensive_data.get('sentiment', {}),
                news_data=comprehensive_data.get('news', {}),
                social_data=comprehensive_data.get('social', {}),
                onchain_data=comprehensive_data.get('onchain', {}),
                entry_price=entry_price
            )
            
            # Call LLM
            response = await self.llm_client.analyze_market_conditions(
                symbol=symbol,
                price_data=comprehensive_data.get('technical', {}),
                indicators=comprehensive_data.get('technical', {}),
                sentiment=comprehensive_data.get('sentiment', {})
            )
            
            if not response:
                return self._default_validation("LLM call failed")
            
            # If LLM returned custom format, try to parse it
            if 'recommendation' in response:
                # Convert LLM's default format to our validation format
                validation = self._convert_llm_response(response, signal)
            else:
                validation = response
            
            # Validate response structure
            validation = self._validate_response_structure(validation)
            
            # Cache the result for future use
            if self.cache_manager:
                cache_key = self.cache_manager.get_cache_key(
                    'ai_analysis',
                    symbol,
                    strategy=strategy_name
                )
                await self.cache_manager.set_cached_analysis(
                    cache_key,
                    validation,
                    ttl=self.cache_ttl
                )
            
            return validation
            
        except Exception as e:
            log.error(f"Error in realtime validation: {e}")
            return self._default_validation(f"Realtime error: {str(e)}")
    
    async def _cached_validation(
        self,
        strategy_name: str,
        signal: Signal,
        symbol: str,
        comprehensive_data: Dict,
        entry_price: Optional[float]
    ) -> Dict:
        """Try to use cached AI validation"""
        # Check cache first
        if self.cache_manager:
            cache_key = self.cache_manager.get_cache_key(
                'ai_analysis',
                symbol,
                strategy=strategy_name
            )
            
            cached = await self.cache_manager.get_cached_analysis(cache_key)
            
            if cached:
                # Update with current data
                cached['from_cache'] = True
                return cached
        
        # Cache miss - do realtime analysis
        log.info("Cache miss, falling back to realtime analysis")
        return await self._realtime_validation(
            strategy_name,
            signal,
            symbol,
            comprehensive_data,
            entry_price
        )
    
    def _convert_llm_response(self, llm_response: Dict, signal: Signal) -> Dict:
        """Convert LLM's default response format to validation format"""
        recommendation = llm_response.get('recommendation', 'hold')
        confidence_raw = llm_response.get('confidence', 0.5)
        
        # Convert confidence from 0-1 to 0-100
        confidence = int(confidence_raw * 100) if confidence_raw <= 1 else int(confidence_raw)
        
        # Determine validation
        if recommendation == signal.value:
            validation = "agree"
        elif recommendation == "hold":
            validation = "partial"
        else:
            validation = "disagree"
        
        return {
            'validation': validation,
            'confidence': confidence,
            'position_multiplier': 1.0,
            'adjusted_entry': None,
            'adjusted_stop_loss': None,
            'adjusted_take_profit': None,
            'key_risks': [llm_response.get('risk', 'Unknown risk')],
            'reasoning': llm_response.get('reasoning', 'AI analysis complete'),
            'time_horizon': 'medium',
            'data_quality_score': 7
        }
    
    def _validate_response_structure(self, response: Dict) -> Dict:
        """Ensure response has all required fields with defaults"""
        defaults = {
            'validation': 'partial',
            'confidence': 50,
            'position_multiplier': 1.0,
            'adjusted_entry': None,
            'adjusted_stop_loss': None,
            'adjusted_take_profit': None,
            'key_risks': ['Unknown'],
            'reasoning': 'No reasoning provided',
            'time_horizon': 'medium',
            'data_quality_score': 5,
            'from_cache': False
        }
        
        # Merge with defaults
        for key, default_value in defaults.items():
            if key not in response:
                response[key] = default_value
        
        # Ensure confidence is in range
        response['confidence'] = max(0, min(100, response['confidence']))
        
        # Ensure position_multiplier is in range
        response['position_multiplier'] = max(0.5, min(1.5, response['position_multiplier']))
        
        return response
    
    def _default_validation(self, reason: str = "No AI analysis available") -> Dict:
        """Return default validation when AI is unavailable"""
        return {
            'validation': 'partial',
            'confidence': 50,
            'position_multiplier': 1.0,
            'adjusted_entry': None,
            'adjusted_stop_loss': None,
            'adjusted_take_profit': None,
            'key_risks': [reason],
            'reasoning': reason,
            'time_horizon': 'medium',
            'data_quality_score': 0,
            'from_cache': False,
            'analysis_mode': 'fallback'
        }
    
    async def get_market_overview(
        self,
        symbol: str,
        df: Optional[pd.DataFrame] = None
    ) -> Optional[Dict]:
        """
        Get general market overview (non-signal specific)
        
        Args:
            symbol: Trading symbol
            df: Optional DataFrame with market data
        
        Returns:
            Market overview analysis
        """
        try:
            # Get comprehensive data
            comprehensive_data = await self.data_aggregator.get_comprehensive_data(
                symbol=symbol,
                df=df
            )
            
            # Check cache first
            if self.cache_manager:
                cache_key = f"market_overview:{symbol}"
                cached = await self.cache_manager.get_cached_analysis(cache_key)
                
                if cached:
                    cached['from_cache'] = True
                    return cached
            
            # Generate prompt
            prompt = get_market_analysis_prompt(symbol, comprehensive_data)
            
            # Call LLM (simplified call)
            # For now, return aggregated sentiment
            aggregated = self.data_aggregator.get_aggregated_sentiment(comprehensive_data)
            
            overview = {
                'symbol': symbol,
                'aggregated_sentiment': aggregated,
                'comprehensive_data': comprehensive_data,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Cache the result
            if self.cache_manager:
                await self.cache_manager.set_cached_analysis(
                    f"market_overview:{symbol}",
                    overview,
                    ttl=7200  # 2 hours for overview
                )
            
            return overview
            
        except Exception as e:
            log.error(f"Error getting market overview: {e}")
            return None
    
    async def invalidate_cache(self, symbol: str):
        """Invalidate cached analysis for a symbol"""
        if self.cache_manager:
            await self.cache_manager.invalidate_symbol(symbol)
    
    def should_execute_trade(self, validation: Dict) -> bool:
        """
        Determine if a trade should be executed based on AI validation
        
        Args:
            validation: AI validation results
        
        Returns:
            True if trade should be executed
        """
        # Check confidence threshold
        if validation['confidence'] < self.min_confidence:
            log.info(f"Trade rejected: confidence {validation['confidence']}% < {self.min_confidence}%")
            return False
        
        # Check validation status
        if validation['validation'] == 'disagree':
            log.info("Trade rejected: AI disagrees with signal")
            return False
        
        # Check data quality
        if validation.get('data_quality_score', 10) < 3:
            log.warning("Trade rejected: poor data quality")
            return False
        
        return True
    
    async def close(self):
        """Cleanup resources"""
        await self.data_aggregator.close()

