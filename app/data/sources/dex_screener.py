"""
DEX Screener API integration for DEX trading data
"""
import aiohttp
from typing import Optional, Dict, List
from app.utils.logger import log


class DexScreenerClient:
    """DEX Screener API client"""
    
    BASE_URL = "https://api.dexscreener.com/latest"
    
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
    
    async def search_pairs(self, query: str) -> Optional[Dict]:
        """Search for trading pairs"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/dex/search"
            params = {'q': query}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"DEX Screener API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error searching pairs on DEX Screener: {e}")
            return None
    
    async def get_pair_by_address(self, chain: str, pair_address: str) -> Optional[Dict]:
        """Get pair data by address"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/dex/pairs/{chain}/{pair_address}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"DEX Screener API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching pair from DEX Screener: {e}")
            return None
    
    async def get_token_pairs(self, token_address: str) -> Optional[Dict]:
        """Get all pairs for a token address"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/dex/tokens/{token_address}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"DEX Screener API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching token pairs from DEX Screener: {e}")
            return None
    
    async def get_latest_pairs(self) -> Optional[Dict]:
        """Get latest token pairs"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/dex/pairs/latest"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"DEX Screener API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching latest pairs from DEX Screener: {e}")
            return None
    
    async def get_trending_pairs(self, chain: Optional[str] = None) -> Optional[List[Dict]]:
        """Get trending pairs (unofficial endpoint)"""
        try:
            # Note: This might need adjustment based on actual API
            pairs_data = await self.get_latest_pairs()
            if pairs_data and 'pairs' in pairs_data:
                pairs = pairs_data['pairs']
                
                # Filter by chain if specified
                if chain:
                    pairs = [p for p in pairs if p.get('chainId') == chain]
                
                # Sort by volume or liquidity
                pairs.sort(key=lambda x: x.get('volume', {}).get('h24', 0), reverse=True)
                
                return pairs[:50]  # Top 50
            
            return []
        except Exception as e:
            log.error(f"Error fetching trending pairs from DEX Screener: {e}")
            return None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

