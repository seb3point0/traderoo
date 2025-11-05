"""
DeFi Llama API integration for DeFi protocol data
"""
import aiohttp
from typing import Optional, Dict, List
from app.utils.logger import log


class DeFiLlamaClient:
    """DeFi Llama API client"""
    
    BASE_URL = "https://api.llama.fi"
    
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
    
    async def get_protocols(self) -> Optional[List[Dict]]:
        """Get all DeFi protocols"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/protocols"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"DeFi Llama API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching protocols from DeFi Llama: {e}")
            return None
    
    async def get_protocol(self, protocol_slug: str) -> Optional[Dict]:
        """Get specific protocol data"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/protocol/{protocol_slug}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"DeFi Llama API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching protocol from DeFi Llama: {e}")
            return None
    
    async def get_tvl(self) -> Optional[Dict]:
        """Get total value locked across all chains"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/charts"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"DeFi Llama API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching TVL from DeFi Llama: {e}")
            return None
    
    async def get_chain_tvl(self, chain: str) -> Optional[Dict]:
        """Get TVL for a specific chain"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/charts/{chain}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"DeFi Llama API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching chain TVL from DeFi Llama: {e}")
            return None
    
    async def get_stablecoins(self) -> Optional[Dict]:
        """Get stablecoin data"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/stablecoins"
            params = {'includePrices': 'true'}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"DeFi Llama API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching stablecoins from DeFi Llama: {e}")
            return None
    
    async def get_yields(self) -> Optional[List[Dict]]:
        """Get yield data for various pools"""
        try:
            session = await self._get_session()
            url = "https://yields.llama.fi/pools"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                else:
                    log.warning(f"DeFi Llama yields API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching yields from DeFi Llama: {e}")
            return None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

