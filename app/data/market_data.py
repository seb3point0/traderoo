"""
Market data aggregation and management
"""
import pandas as pd
from typing import Optional, List
from datetime import datetime, timedelta
from app.core.exchange_manager import ExchangeManager
from app.data.indicators import TechnicalIndicators
from app.utils.logger import log


class MarketDataManager:
    """Manages market data fetching and processing"""
    
    def __init__(self, exchange: ExchangeManager):
        self.exchange = exchange
        self.cache = {}
        self.last_update = {}
    
    async def get_ohlcv_df(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 500,
        with_indicators: bool = True
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data and convert to pandas DataFrame
        
        Args:
            symbol: Trading pair symbol
            timeframe: Candle timeframe
            limit: Number of candles to fetch
            with_indicators: Whether to add technical indicators
        
        Returns:
            DataFrame with OHLCV data and indicators
        """
        try:
            # Fetch OHLCV data
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                log.warning(f"No OHLCV data received for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Add technical indicators if requested
            if with_indicators:
                df = TechnicalIndicators.add_all_indicators(df)
            
            # Cache the data
            cache_key = f"{symbol}:{timeframe}"
            self.cache[cache_key] = df
            self.last_update[cache_key] = datetime.utcnow()
            
            log.debug(f"Fetched {len(df)} candles for {symbol} ({timeframe})")
            
            return df
            
        except Exception as e:
            log.error(f"Error fetching OHLCV data for {symbol}: {e}")
            return pd.DataFrame()
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker.get('last') or ticker.get('close')
        except Exception as e:
            log.error(f"Error fetching current price for {symbol}: {e}")
            return None
    
    async def get_multiple_prices(self, symbols: List[str]) -> dict:
        """Get current prices for multiple symbols"""
        prices = {}
        for symbol in symbols:
            price = await self.get_current_price(symbol)
            if price:
                prices[symbol] = price
        return prices
    
    async def get_orderbook_spread(self, symbol: str) -> tuple[float, float, float]:
        """
        Get orderbook bid-ask spread
        Returns: (bid, ask, spread_percentage)
        """
        try:
            orderbook = await self.exchange.fetch_orderbook(symbol, limit=1)
            
            if orderbook['bids'] and orderbook['asks']:
                bid = orderbook['bids'][0][0]
                ask = orderbook['asks'][0][0]
                spread_pct = ((ask - bid) / bid) * 100
                return bid, ask, spread_pct
            
            return 0.0, 0.0, 0.0
            
        except Exception as e:
            log.error(f"Error fetching orderbook for {symbol}: {e}")
            return 0.0, 0.0, 0.0
    
    async def get_volume_profile(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> dict:
        """Get volume profile data"""
        try:
            df = await self.get_ohlcv_df(symbol, timeframe, limit, with_indicators=False)
            
            if df.empty:
                return {}
            
            total_volume = df['volume'].sum()
            avg_volume = df['volume'].mean()
            current_volume = df['volume'].iloc[-1]
            
            # Volume trend (increasing/decreasing)
            volume_sma = df['volume'].rolling(window=5).mean()
            volume_trend = "increasing" if volume_sma.iloc[-1] > volume_sma.iloc[-5] else "decreasing"
            
            return {
                "total_volume": total_volume,
                "average_volume": avg_volume,
                "current_volume": current_volume,
                "volume_ratio": current_volume / avg_volume if avg_volume > 0 else 0,
                "volume_trend": volume_trend
            }
            
        except Exception as e:
            log.error(f"Error calculating volume profile: {e}")
            return {}
    
    def get_cached_data(self, symbol: str, timeframe: str, max_age_seconds: int = 60) -> Optional[pd.DataFrame]:
        """Get cached data if fresh enough"""
        cache_key = f"{symbol}:{timeframe}"
        
        if cache_key in self.cache:
            last_update = self.last_update.get(cache_key)
            if last_update and (datetime.utcnow() - last_update).seconds < max_age_seconds:
                return self.cache[cache_key]
        
        return None
    
    def clear_cache(self, symbol: Optional[str] = None):
        """Clear cached data"""
        if symbol:
            keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{symbol}:")]
            for key in keys_to_remove:
                del self.cache[key]
                del self.last_update[key]
        else:
            self.cache.clear()
            self.last_update.clear()

