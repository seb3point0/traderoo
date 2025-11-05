"""
CoinGecko API integration for market data
"""
import aiohttp
from typing import Optional, Dict, List
from app.utils.logger import log
from app.config import get_settings

settings = get_settings()


class CoinGeckoClient:
    """CoinGecko API client"""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.coingecko_api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                headers['x-cg-pro-api-key'] = self.api_key
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_coin_data(self, coin_id: str) -> Optional[Dict]:
        """Get comprehensive coin data"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/coins/{coin_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'true',
                'developer_data': 'false'
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"CoinGecko API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching coin data from CoinGecko: {e}")
            return None
    
    async def get_price(self, coin_ids: List[str], vs_currencies: List[str] = ['usd']) -> Optional[Dict]:
        """Get simple price for coins"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/simple/price"
            params = {
                'ids': ','.join(coin_ids),
                'vs_currencies': ','.join(vs_currencies),
                'include_24hr_change': 'true',
                'include_market_cap': 'true',
                'include_24hr_vol': 'true'
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"CoinGecko API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching prices from CoinGecko: {e}")
            return None
    
    async def get_trending(self) -> Optional[Dict]:
        """Get trending coins"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/search/trending"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"CoinGecko API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching trending coins from CoinGecko: {e}")
            return None
    
    async def get_market_data(
        self,
        vs_currency: str = 'usd',
        order: str = 'market_cap_desc',
        per_page: int = 100,
        page: int = 1
    ) -> Optional[List[Dict]]:
        """Get market data for coins"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/coins/markets"
            params = {
                'vs_currency': vs_currency,
                'order': order,
                'per_page': per_page,
                'page': page,
                'sparkline': 'false'
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"CoinGecko API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching market data from CoinGecko: {e}")
            return None
    
    async def get_global_data(self) -> Optional[Dict]:
        """Get global cryptocurrency data"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/global"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {})
                else:
                    log.warning(f"CoinGecko API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching global data from CoinGecko: {e}")
            return None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

